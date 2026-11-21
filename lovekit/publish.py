"""Publishing an agent's streams: declared once, kept live, given up only when replaced.

An app that offers live sources (cameras, detectors, microphones, spectrometers) says which
with :meth:`lovekit.Lovekit.publish`, and sends frames to them for as long as it runs::

    spectrum = DataStream("spectrum", dtype="float16", shape=(512,), axes=[Axis("wavelength", AxisType.SPECTRUM)])
    async with lovekit.publish([VideoStream("camera", title="Main camera"), spectrum]) as live:
        state.streams = live.streams          # what the UI renders (@lovekit/stream)
        while True:
            await live.video("camera").send(rgba)     # an (height, width, 4) uint8 array
            await live.data("spectrum").send(values)  # an array as declared

The declaration is the agent's whole set (``declareStreams``): a stream keeps its id over
restarts, and one the app no longer names is removed. So one process publishes once at a
time: a second :meth:`~lovekit.Lovekit.publish` on the same client raises.

How the frames travel is the transport's (:mod:`lovekit.transports`), named by the connection
lovekit hands out. The connection is kept:

- A video track is made on the first frame, sized from it, and made again when the size
  changes. The last frame of a video or data stream is sent again while no new one comes, so
  a viewer who joins late, or after a reconnect, sees it.
- A data stream is lossy and holds one value: a frame that cannot be sent is dropped, and a
  newer one replaces an unsent one.
- When the connection drops (network, server restart) a fresh one is taken and joined again,
  with backoff, and every stream is published again with its last frame. While lovekit cannot
  be reached (an app that boots before it), the declaration is tried again the same way; what
  lovekit refuses (a blank key) raises.
- When another process of the same agent connects, or an operator removes the publisher, this
  one stops for good: two processes of one agent would otherwise take the room from each
  other forever. :attr:`LiveStreams.stopped` is set, and ``send`` does nothing from then on.
"""

from __future__ import annotations

import asyncio
import logging
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from types import TracebackType
from typing import TYPE_CHECKING

import numpy as np
from rath.operation import GraphQLException

from lovekit import frames
from lovekit.api.schema import AxisInput, AxisType, CalibrationInput, DataFormatInput, Stream, StreamDeclarationInput, StreamKind, Transport

if TYPE_CHECKING:
    from lovekit.lovekit import Lovekit
    from lovekit.transports.livekit import AudioSink, DataSink, Gone, Session, VideoSink

logger = logging.getLogger(__name__)

#: How often the last frame of a video or data stream is sent again while no new one comes.
RESEND_INTERVAL = 0.5
#: The longest wait between two attempts to join again.
MAX_BACKOFF = 30.0


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


@dataclass(frozen=True)
class Axis:
    """One axis of a data stream's frames, named as mikro's coordinate systems name theirs."""

    name: str
    type: AxisType


@dataclass(frozen=True)
class Calibration:
    """What a step along an axis measures: position = offset + scale * index, in unit."""

    axis: str
    unit: str
    scale: float = 1.0
    offset: float = 0.0


@dataclass(frozen=True)
class DataStream:
    """A stream of values to offer: a spectrum, a trace, a small profile.

    A frame is one array of ``dtype`` and ``shape``, at most 1024 bytes
    (:data:`lovekit.frames.MAX_FRAME_BYTES`): 512 float16 values, 256 float32.
    """

    key: str
    """The agent's own name for it, the same on every start."""
    dtype: str
    """The type of one value, as numpy names it."""
    shape: tuple[int, ...]
    axes: Sequence[Axis]
    """One per dimension of the shape, in its order."""
    title: str | None = None
    description: str | None = None
    calibration: Sequence[Calibration] = ()
    unit: str | None = None
    """The unit of the values themselves."""
    reference: str | None = None
    """The space the axes are in, named as mikro names a coordinate system's reference."""
    max_rate: float = 30.0
    """The most frames a second that are sent; one sent sooner replaces the one waiting."""

    def __post_init__(self) -> None:
        object.__setattr__(self, "shape", tuple(self.shape))
        size = math.prod(self.shape) * np.dtype(self.dtype).itemsize
        if size > frames.MAX_FRAME_BYTES:
            raise ValueError(f"{self.key}: a frame of {size} bytes is more than the {frames.MAX_FRAME_BYTES} a data stream carries; send fewer or smaller values")
        if len(self.axes) != len(self.shape):
            raise ValueError(f"{self.key}: {len(self.shape)} dimensions, but {len(self.axes)} axes")

    @property
    def kind(self) -> StreamKind:
        return StreamKind.DATA

    def format(self) -> DataFormatInput:
        return DataFormatInput(
            dtype=self.dtype,
            shape=self.shape,
            axes=tuple(AxisInput(name=axis.name, type=axis.type) for axis in self.axes),
            calibration=tuple(CalibrationInput(axis=c.axis, unit=c.unit, scale=c.scale, offset=c.offset) for c in self.calibration),
            unit=self.unit,
            reference=self.reference,
        )


Declaration = VideoStream | AudioStream | DataStream


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
    """The track of one video stream: what ``live.video(key)`` is."""

    def __init__(self, declaration: VideoStream, live: LiveStreams) -> None:
        self.declaration = declaration
        self._live = live
        self._session: Session | None = None
        self._sink: VideoSink | None = None
        self._last: np.ndarray | None = None
        self._sent_at = 0.0
        self._lock = asyncio.Lock()

    @property
    def key(self) -> str:
        return self.declaration.key

    async def send(self, rgba: np.ndarray) -> None:
        """Send one RGBA frame, (height, width, 4) of uint8 (see :func:`to_rgba` for others).

        Kept as the last frame while the connection is away, and sent once it is back.
        """
        if rgba.ndim != 3 or rgba.shape[2] != 4 or rgba.dtype != np.uint8:
            raise ValueError(f"A frame is (height, width, 4) uint8 RGBA, not {rgba.shape} {rgba.dtype}: see lovekit.publish.to_rgba")
        self._last = rgba
        await self._push()

    async def _push(self) -> None:
        async with self._lock:
            frame, session = self._last, self._session
            if frame is None or session is None or self._live.stopped.is_set():
                return
            height, width = frame.shape[:2]
            if self._sink is None or self._sink.size != (width, height):
                if self._sink is not None:
                    await self._sink.aclose()
                self._sink = await session.video(self.key, width, height, self.declaration.max_framerate, self.declaration.max_bitrate)
            self._sink.push(frame)
            self._sent_at = asyncio.get_running_loop().time()

    async def _resend_if_idle(self) -> None:
        if self._session is not None and asyncio.get_running_loop().time() - self._sent_at >= RESEND_INTERVAL:
            await self._push()

    async def _attach(self, session: Session) -> None:
        """A (new) session: the track is published there again with the last frame."""
        await self._detach()
        self._session = session
        await self._push()

    async def _detach(self) -> None:
        """The session is gone; the track goes with it."""
        async with self._lock:
            self._session = None
            if self._sink is not None:
                await self._sink.aclose()
                self._sink = None


class AudioTrack:
    """The track of one audio stream: what ``live.audio(key)`` is."""

    def __init__(self, declaration: AudioStream, live: LiveStreams) -> None:
        self.declaration = declaration
        self._live = live
        self._sink: AudioSink | None = None
        self._lock = asyncio.Lock()

    @property
    def key(self) -> str:
        return self.declaration.key

    async def send(self, samples: np.ndarray) -> None:
        """Send int16 samples, (samples,) or (samples, channels). Dropped while the connection is away."""
        data = np.asarray(samples, dtype=np.int16)
        channels = self.declaration.num_channels
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        if data.shape[1] != channels:
            raise ValueError(f"{self.key} has {channels} channels, not {data.shape[1]}")
        async with self._lock:
            if self._sink is None or self._live.stopped.is_set():
                return
            await self._sink.push(data)

    async def _resend_if_idle(self) -> None:
        return None

    async def _attach(self, session: Session) -> None:
        await self._detach()
        async with self._lock:
            self._sink = await session.audio(self.key, self.declaration.sample_rate, self.declaration.num_channels)

    async def _detach(self) -> None:
        async with self._lock:
            if self._sink is not None:
                await self._sink.aclose()
                self._sink = None


class DataTrack:
    """The track of one data stream: what ``live.data(key)`` is."""

    def __init__(self, declaration: DataStream, live: LiveStreams) -> None:
        self.declaration = declaration
        self._live = live
        self._dtype = np.dtype(declaration.dtype)
        self._sink: DataSink | None = None
        self._packet: bytes | None = None
        self._sequence = 0
        self._sent_at = 0.0
        self._waiting = False

    @property
    def key(self) -> str:
        return self.declaration.key

    @property
    def watched(self) -> bool:
        """Whether anyone may be watching. Never false while someone is: true may be nobody."""
        return self._live._watched.is_set()

    async def wait_watched(self) -> None:
        """Until someone may be watching: an app need not measure for nobody."""
        await self._live._watched.wait()

    async def send(self, values: np.ndarray) -> None:
        """Send one frame, an array of the declared dtype and shape.

        Never queued: sent now, or kept as the one value that waits (for ``max_rate``, or
        for the connection to be back), where a newer one replaces it.
        """
        data = np.asarray(values)
        if data.dtype != self._dtype or data.shape != self.declaration.shape:
            raise ValueError(f"A frame of {self.key} is {self.declaration.shape} {self._dtype}, not {data.shape} {data.dtype}")
        self._sequence += 1
        self._packet = frames.encode(self._sequence, data)
        self._waiting = True
        if asyncio.get_running_loop().time() - self._sent_at >= 1.0 / self.declaration.max_rate:
            self._flush()

    def _flush(self) -> None:
        if self._sink is None or self._packet is None or self._live.stopped.is_set():
            return
        self._sink.push(self._packet)
        self._sent_at = asyncio.get_running_loop().time()
        self._waiting = False

    async def _resend_if_idle(self) -> None:
        idle = asyncio.get_running_loop().time() - self._sent_at
        if idle >= (1.0 / self.declaration.max_rate if self._waiting else RESEND_INTERVAL):
            self._flush()

    async def _attach(self, session: Session) -> None:
        await self._detach()
        self._sink = await session.data(self.key)
        self._flush()

    async def _detach(self) -> None:
        if self._sink is not None:
            sink, self._sink = self._sink, None
            await sink.aclose()


Track = VideoTrack | AudioTrack | DataTrack


def _track(declaration: Declaration, live: LiveStreams) -> Track:
    if isinstance(declaration, VideoStream):
        return VideoTrack(declaration, live)
    if isinstance(declaration, AudioStream):
        return AudioTrack(declaration, live)
    return DataTrack(declaration, live)


class LiveStreams:
    """An agent's declared streams while they are published: what ``lovekit.publish(...)`` gives.

    ``live.streams`` are the declared streams (hand them to a state for the UI);
    ``live.video(key)``, ``live.audio(key)`` and ``live.data(key)`` are the tracks to send to.
    """

    def __init__(self, lovekit: Lovekit, declarations: Sequence[Declaration]) -> None:
        keys = [declaration.key for declaration in declarations]
        duplicates = sorted({key for key in keys if keys.count(key) > 1})
        if duplicates:
            raise ValueError(f"Each stream is declared once; declared more than once: {', '.join(duplicates)}")
        self._lovekit = lovekit
        self._declarations = list(declarations)
        self._tracks: dict[str, Track] = {declaration.key: _track(declaration, self) for declaration in self._declarations}
        self.streams: tuple[Stream, ...] = ()
        """The declared streams, as lovekit keeps them (their ids stay over restarts)."""
        self.connected = asyncio.Event()
        """Set while joined and every track published."""
        self.stopped = asyncio.Event()
        """Set once publishing ended for good: closed, replaced by another process, or removed."""
        self.stop_reason: str | None = None
        self.joins = 0
        """How often it joined: more than once after the connection dropped and was joined again."""
        self._watched = asyncio.Event()
        self._session: Session | None = None
        self._tasks: list[asyncio.Task[None]] = []
        self._closing = False

    def __getitem__(self, key: str) -> Track:
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

    def data(self, key: str) -> DataTrack:
        """The data track of ``key``."""
        track = self._tracks[key]
        if not isinstance(track, DataTrack):
            raise TypeError(f"{key} is not a data stream")
        return track

    async def wait_connected(self, timeout: float | None = None) -> None:
        """Until joined (again)."""
        await asyncio.wait_for(self.connected.wait(), timeout)

    async def wait_stopped(self) -> str | None:
        """Until publishing ended for good; why it did."""
        await self.stopped.wait()
        return self.stop_reason

    async def _declare_until_answered(self) -> None:
        """Declare, again and again while lovekit cannot be reached; what it refuses raises."""
        backoff = 1.0
        while True:
            try:
                await self._declare()
                return
            except (GraphQLException, asyncio.CancelledError):
                raise
            except Exception as error:  # lovekit is not there (yet)
                logger.warning("Could not declare %s, again in %.0f s: %s", ", ".join(self._tracks), backoff, error)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF)

    async def _declare(self) -> None:
        self.streams = await self._lovekit.adeclare_streams(
            [
                StreamDeclarationInput(
                    key=declaration.key,
                    title=declaration.title or declaration.key,
                    kind=declaration.kind,
                    description=declaration.description,
                    format=declaration.format() if isinstance(declaration, DataStream) else None,
                )
                for declaration in self._declarations
            ]
        )

    def _watchers(self, count: int) -> None:
        if count:
            self._watched.set()
        else:
            self._watched.clear()

    async def _join(self) -> Session:
        connection = await self._lovekit.apublisher_connection()
        if connection.transport != Transport.LIVEKIT:
            raise RuntimeError(f"lovekit hands out a {connection.transport} connection, which this lovekit client does not speak")
        if self._lovekit.livekit is None:
            raise RuntimeError("this lovekit client was built without the livekit alias")
        from lovekit.transports import livekit

        return await livekit.ajoin(self._lovekit.livekit, connection.credential, self._watchers)

    async def _connect(self) -> Gone:
        """Join once and publish every track; returns why the session went away."""
        session = await self._join()
        self._session = session
        try:
            for track in self._tracks.values():
                await track._attach(session)
            self.joins += 1
            self.connected.set()
            return await session.wait_gone()
        finally:
            self.connected.clear()
            self._watched.clear()
            self._session = None
            for track in self._tracks.values():
                await track._detach()
            await session.aclose()

    async def _run(self) -> None:
        backoff = 1.0
        while not self._closing:
            try:
                gone = await self._connect()
            except asyncio.CancelledError:
                raise
            except Exception as error:  # a connection, a join that failed: try again, later
                logger.warning("Could not join for %s, again in %.0f s: %s", ", ".join(self._tracks), backoff, error)
                await asyncio.sleep(backoff)
                if isinstance(error, GraphQLException):
                    # lovekit answered, but knows no agent of ours (its database was reset):
                    # declared again, there is one, with the same streams.
                    try:
                        await self._declare()
                    except Exception as again:  # it is tried once more on the next round
                        logger.debug("Declaring again failed: %s", again)
                backoff = min(backoff * 2, MAX_BACKOFF)
                continue
            backoff = 1.0
            if gone.final:
                self._stop(gone.reason)
                if not gone.closed:
                    logger.warning("Stopped publishing %s: %s", ", ".join(self._tracks), self.stop_reason)
                return
            logger.info("The connection went away (%s); joining again", gone.reason)

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
        try:
            await self._declare_until_answered()
        except BaseException:
            # Never entered, so never exited: the client may publish again.
            self._stop("not declared")
            self._lovekit._release_publisher(self)
            raise
        self._tasks = [asyncio.create_task(self._run()), asyncio.create_task(self._resend())]
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None) -> None:
        self._closing = True
        session = self._session
        if session is not None:
            await session.aclose()
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        for track in self._tracks.values():
            await track._detach()
        self._stop("closed")
        self._lovekit._release_publisher(self)


def declarations(streams: Iterable[Declaration]) -> list[Declaration]:
    """``streams`` as a list, each a :class:`VideoStream`, an :class:`AudioStream` or a :class:`DataStream`."""
    listed = list(streams)
    for stream in listed:
        if not isinstance(stream, (VideoStream, AudioStream, DataStream)):
            raise TypeError(f"Not a stream declaration: {stream!r}")
    return listed
