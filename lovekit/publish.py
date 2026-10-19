"""Publishing an agent's streams: declared once, kept live, given up only when replaced.

An app that offers live sources (cameras, detectors, microphones) says which with
:meth:`lovekit.Lovekit.publish`, and sends frames to them for as long as it runs::

    async with lovekit.publish([VideoStream("camera", title="Main camera")]) as live:
        state.streams = live.streams          # what the UI renders (@lovekit/stream)
        while True:
            await live["camera"].send(rgba)   # an (height, width, 4) uint8 array

The declaration is the agent's whole set (``declareStreams``): a stream keeps its id over
restarts, and one the app no longer names is removed. So one process publishes once at a
time: a second :meth:`~lovekit.Lovekit.publish` on the same client raises.

Underneath, every stream is a track of the agent's LiveKit room named by its key, published
as the agent's one participant. The connection is kept:

- A track is made on the first frame, sized from it, and made again when the size changes.
  The last frame is sent again while no new one comes, so a viewer who joins late, or after a
  reconnect, sees a picture.
- When the room drops (network, server restart, the room closing) a fresh token is taken and
  the room joined again, with backoff, and every track is published again with its last frame.
- When another process of the same agent connects (``DUPLICATE_IDENTITY``), or an operator
  removes the participant (``PARTICIPANT_REMOVED``), this one stops for good: two processes of
  one agent would otherwise take the room from each other forever. :attr:`LiveStreams.stopped`
  is set, and ``send`` does nothing from then on.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from types import TracebackType
from typing import TYPE_CHECKING

import numpy as np
from livekit import rtc

from lovekit.api.schema import Stream, StreamDeclarationInput, StreamKind

if TYPE_CHECKING:
    from lovekit.lovekit import Lovekit

logger = logging.getLogger(__name__)

#: How often the last frame of a video stream is sent again while no new one comes.
RESEND_INTERVAL = 0.5
#: The longest wait between two attempts to join the room again.
MAX_BACKOFF = 30.0

_FINAL = {
    rtc.DisconnectReason.DUPLICATE_IDENTITY: "replaced by a newer connection of this agent",
    rtc.DisconnectReason.PARTICIPANT_REMOVED: "removed from the room",
    rtc.DisconnectReason.CLIENT_INITIATED: "closed",
}


@dataclass(frozen=True)
class VideoStream:
    """A video stream to offer: a camera, a detector."""

    key: str
    """The agent's own name for it, the same on every start: the track's name."""
    title: str | None = None
    description: str | None = None
    max_framerate: float = 15.0
    max_bitrate: int = 3_000_000

    @property
    def kind(self) -> StreamKind:
        return StreamKind.VIDEO


@dataclass(frozen=True)
class AudioStream:
    """An audio stream to offer: a microphone."""

    key: str
    """The agent's own name for it, the same on every start: the track's name."""
    title: str | None = None
    description: str | None = None
    sample_rate: int = 48_000
    num_channels: int = 1

    @property
    def kind(self) -> StreamKind:
        return StreamKind.AUDIO


def to_rgba(frame: np.ndarray) -> np.ndarray:
    """An image as the RGBA bytes a video track takes.

    A gray image (height, width) is stretched between its 1st and 99.9th percentile: a
    uint16 frame shifted down to eight bits shows nothing of a dim sample. An RGB image
    (height, width, 3) of uint8 gets an opaque alpha; an RGBA uint8 image is taken as it is.
    """
    data = np.asarray(frame)
    if data.ndim == 3 and data.shape[2] == 4 and data.dtype == np.uint8:
        return data
    if data.ndim == 3 and data.shape[2] == 3 and data.dtype == np.uint8:
        rgba = np.empty((*data.shape[:2], 4), dtype=np.uint8)
        rgba[..., :3] = data
        rgba[..., 3] = 255
        return rgba
    if data.ndim != 2:
        raise ValueError(f"Not an image: shape {data.shape}, dtype {data.dtype}")
    gray = data.astype(np.float32)
    low, high = np.percentile(gray, (1.0, 99.9))
    scale = 255.0 / (high - low) if high > low else 0.0
    eight = np.clip((gray - low) * scale, 0, 255).astype(np.uint8)
    rgba = np.empty((*eight.shape, 4), dtype=np.uint8)
    rgba[..., :3] = eight[..., None]
    rgba[..., 3] = 255
    return rgba


class VideoTrack:
    """The track of one video stream: what ``live[key]`` is."""

    def __init__(self, declaration: VideoStream, live: LiveStreams) -> None:
        self.declaration = declaration
        self._live = live
        self._room: rtc.Room | None = None
        self._source: rtc.VideoSource | None = None
        self._sid: str | None = None
        self._size: tuple[int, int] | None = None
        self._last: np.ndarray | None = None
        self._sent_at = 0.0
        self._lock = asyncio.Lock()

    @property
    def key(self) -> str:
        return self.declaration.key

    async def send(self, rgba: np.ndarray) -> None:
        """Send one RGBA frame, (height, width, 4) of uint8 (see :func:`to_rgba` for others).

        Kept as the last frame while the room is away, and sent once it is back.
        """
        if rgba.ndim != 3 or rgba.shape[2] != 4 or rgba.dtype != np.uint8:
            raise ValueError(f"A frame is (height, width, 4) uint8 RGBA, not {rgba.shape} {rgba.dtype}: see lovekit.publish.to_rgba")
        self._last = rgba
        await self._push()

    async def _push(self) -> None:
        async with self._lock:
            frame, room = self._last, self._room
            if frame is None or room is None or self._live.stopped.is_set():
                return
            height, width = frame.shape[:2]
            if self._size != (width, height) or self._source is None:
                await self._unpublish()
                self._source = rtc.VideoSource(width, height)
                track = rtc.LocalVideoTrack.create_video_track(self.key, self._source)
                options = rtc.TrackPublishOptions(
                    source=rtc.TrackSource.SOURCE_CAMERA,
                    video_encoding=rtc.VideoEncoding(max_framerate=self.declaration.max_framerate, max_bitrate=self.declaration.max_bitrate),
                )
                self._sid = (await room.local_participant.publish_track(track, options)).sid
                self._size = (width, height)
            self._source.capture_frame(rtc.VideoFrame(width, height, rtc.VideoBufferType.RGBA, frame.tobytes()))
            self._sent_at = asyncio.get_running_loop().time()

    async def _resend_if_idle(self) -> None:
        if self._room is not None and asyncio.get_running_loop().time() - self._sent_at >= RESEND_INTERVAL:
            await self._push()

    async def _attach(self, room: rtc.Room) -> None:
        """A (new) room: the track is published there again with the last frame."""
        async with self._lock:
            self._room = room
            self._sid = None
            self._size = None
            if self._source is not None:
                await self._source.aclose()
                self._source = None
        await self._push()

    async def _detach(self) -> None:
        """The room is gone; the track goes with it."""
        async with self._lock:
            self._room = None
            self._sid = None
            self._size = None
            if self._source is not None:
                await self._source.aclose()
                self._source = None

    async def _unpublish(self) -> None:
        if self._sid is not None and self._room is not None and self._room.isconnected():
            await self._room.local_participant.unpublish_track(self._sid)
        self._sid = None
        if self._source is not None:
            await self._source.aclose()
            self._source = None


class AudioTrack:
    """The track of one audio stream: what ``live[key]`` is."""

    def __init__(self, declaration: AudioStream, live: LiveStreams) -> None:
        self.declaration = declaration
        self._live = live
        self._room: rtc.Room | None = None
        self._source: rtc.AudioSource | None = None
        self._lock = asyncio.Lock()

    @property
    def key(self) -> str:
        return self.declaration.key

    async def send(self, samples: np.ndarray) -> None:
        """Send int16 samples, (samples,) or (samples, channels). Dropped while the room is away."""
        data = np.asarray(samples, dtype=np.int16)
        channels = self.declaration.num_channels
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        if data.shape[1] != channels:
            raise ValueError(f"{self.key} has {channels} channels, not {data.shape[1]}")
        async with self._lock:
            if self._source is None or self._live.stopped.is_set():
                return
            frame = rtc.AudioFrame(data.tobytes(), self.declaration.sample_rate, channels, data.shape[0])
            await self._source.capture_frame(frame)

    async def _resend_if_idle(self) -> None:
        return None

    async def _attach(self, room: rtc.Room) -> None:
        async with self._lock:
            self._room = room
            self._source = rtc.AudioSource(self.declaration.sample_rate, self.declaration.num_channels)
            track = rtc.LocalAudioTrack.create_audio_track(self.key, self._source)
            await room.local_participant.publish_track(track, rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE))

    async def _detach(self) -> None:
        async with self._lock:
            self._room = None
            if self._source is not None:
                await self._source.aclose()
                self._source = None


class LiveStreams:
    """An agent's declared streams while they are published: what ``lovekit.publish(...)`` gives.

    ``live.streams`` are the declared streams (hand them to a state for the UI);
    ``live[key]`` is the track to send to.
    """

    def __init__(self, lovekit: Lovekit, declarations: Sequence[VideoStream | AudioStream]) -> None:
        keys = [declaration.key for declaration in declarations]
        duplicates = sorted({key for key in keys if keys.count(key) > 1})
        if duplicates:
            raise ValueError(f"Each stream is declared once; declared more than once: {', '.join(duplicates)}")
        self._lovekit = lovekit
        self._declarations = list(declarations)
        self._tracks: dict[str, VideoTrack | AudioTrack] = {
            declaration.key: VideoTrack(declaration, self) if isinstance(declaration, VideoStream) else AudioTrack(declaration, self)
            for declaration in self._declarations
        }
        self.streams: tuple[Stream, ...] = ()
        """The declared streams, as lovekit keeps them (their ids stay over restarts)."""
        self.connected = asyncio.Event()
        """Set while the room is joined and every track published."""
        self.stopped = asyncio.Event()
        """Set once publishing ended for good: closed, replaced by another process, or removed."""
        self.stop_reason: str | None = None
        self.joins = 0
        """How often the room was joined: more than once after it dropped and was joined again."""
        self._room: rtc.Room | None = None
        self._tasks: list[asyncio.Task[None]] = []
        self._closing = False

    def __getitem__(self, key: str) -> VideoTrack | AudioTrack:
        return self._tracks[key]

    def video(self, key: str) -> VideoTrack:
        """The video track of ``key``."""
        track = self._tracks[key]
        if not isinstance(track, VideoTrack):
            raise TypeError(f"{key} is not a video stream")
        return track

    def audio(self, key: str) -> AudioTrack:
        """The audio track of ``key``."""
        track = self._tracks[key]
        if not isinstance(track, AudioTrack):
            raise TypeError(f"{key} is not an audio stream")
        return track

    async def wait_connected(self, timeout: float | None = None) -> None:
        """Until the room is joined (again)."""
        await asyncio.wait_for(self.connected.wait(), timeout)

    async def wait_stopped(self) -> str | None:
        """Until publishing ended for good; why it did."""
        await self.stopped.wait()
        return self.stop_reason

    @property
    def room(self) -> rtc.Room | None:
        """The room while it is joined."""
        return self._room

    async def _declare(self) -> None:
        self.streams = await self._lovekit.adeclare_streams(
            [
                StreamDeclarationInput(key=declaration.key, title=declaration.title or declaration.key, kind=declaration.kind, description=declaration.description)
                for declaration in self._declarations
            ]
        )

    async def _connect(self) -> rtc.DisconnectReason.ValueType:
        """Join the room once and publish every track; returns why the room went away."""
        token = await self._lovekit.apublish_token()
        room = rtc.Room()
        gone: asyncio.Future[rtc.DisconnectReason.ValueType] = asyncio.get_running_loop().create_future()

        def disconnected(reason: rtc.DisconnectReason.ValueType) -> None:
            if not gone.done():
                gone.set_result(reason)

        room.on("disconnected", disconnected)
        await self._lovekit.aconnect_room(token, room)
        self._room = room
        try:
            for track in self._tracks.values():
                await track._attach(room)
            self.joins += 1
            self.connected.set()
            return await gone
        finally:
            self.connected.clear()
            self._room = None
            for track in self._tracks.values():
                await track._detach()
            if room.isconnected():
                await room.disconnect()

    async def _run(self) -> None:
        backoff = 1.0
        while not self._closing:
            try:
                reason = await self._connect()
            except asyncio.CancelledError:
                raise
            except Exception as error:  # a token, a join that failed: try again, later
                logger.warning("Could not join the room of %s, again in %.0f s: %s", self._lovekit.__class__.__name__, backoff, error)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF)
                continue
            backoff = 1.0
            if reason in _FINAL:
                self._stop(_FINAL[reason])
                if reason != rtc.DisconnectReason.CLIENT_INITIATED:
                    logger.warning("Stopped publishing %s: %s", ", ".join(self._tracks), self.stop_reason)
                return
            logger.info("The room went away (%s); joining it again", rtc.DisconnectReason.Name(reason))

    async def _resend(self) -> None:
        while True:
            await asyncio.sleep(RESEND_INTERVAL / 2)
            for track in self._tracks.values():
                await track._resend_if_idle()

    def _stop(self, reason: str) -> None:
        if not self.stopped.is_set():
            self.stop_reason = reason
            self.stopped.set()

    async def __aenter__(self) -> LiveStreams:
        await self._declare()
        self._tasks = [asyncio.create_task(self._run()), asyncio.create_task(self._resend())]
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None) -> None:
        self._closing = True
        room = self._room
        if room is not None and room.isconnected():
            await room.disconnect()
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        for track in self._tracks.values():
            await track._detach()
        self._stop("closed")
        self._lovekit._release_publisher(self)


def declarations(streams: Iterable[VideoStream | AudioStream]) -> list[VideoStream | AudioStream]:
    """``streams`` as a list, each a :class:`VideoStream` or an :class:`AudioStream`."""
    listed = list(streams)
    for stream in listed:
        if not isinstance(stream, (VideoStream, AudioStream)):
            raise TypeError(f"Not a stream declaration: {stream!r}")
    return listed
