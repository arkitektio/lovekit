"""The LiveKit transport: an agent's streams as tracks of its room on a LiveKit media server.

The one module that knows LiveKit. :func:`ajoin` joins the room a connection's credential is
for and gives a :class:`Session`; a stream publishes into it through a sink (:meth:`Session.video`,
:meth:`Session.audio`, :meth:`Session.data`): a video or audio stream is a media track, a data
stream a data track, each named by the stream's key.

Connecting, also when the server is only on the mesh:

A room's signaling is a websocket and its media is WebRTC over UDP. Neither
goes through the mesh's HTTP proxy the way the GraphQL clients do. For an SFU
that is only reachable over the deployment's mesh, the alias fakts resolved
carries the mesh node it is reached through, which offers two things instead:

- a local TCP forward to the SFU, which the room connects to for signaling;
- a TURN relay on 127.0.0.1 whose relayed traffic goes over the mesh. The
  room is told to use it as its only ICE server, with a relay-only policy.

That needs no root and no TUN device, but it does need the in-process mesh
node (``pip install "fakts[mesh]"``, ``ARKITEKT_MESH=1``). The SFU has to advertise its mesh
address (LiveKit ``rtc.node_ip``) on its UDP port (``rtc.udp_port``), and the
mesh ACLs must let this node reach both ports.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Any

import numpy as np
from fakts import Alias
from livekit import rtc

_FINAL = {
    rtc.DisconnectReason.DUPLICATE_IDENTITY: "replaced by a newer connection of this agent",
    rtc.DisconnectReason.PARTICIPANT_REMOVED: "removed from the room",
    rtc.DisconnectReason.CLIENT_INITIATED: "closed",
}


@dataclass(frozen=True)
class Gone:
    """Why a session ended; ``final`` when joining again would be wrong."""

    reason: str
    final: bool
    closed: bool = False
    """Ended by this side."""


class VideoSink:
    """One published video track of a fixed size."""

    def __init__(
        self, room: rtc.Room, source: rtc.VideoSource, sid: str, width: int, height: int
    ) -> None:
        self._room, self._source, self._sid = room, source, sid
        self.size = (width, height)

    def push(self, rgba: np.ndarray) -> None:
        width, height = self.size
        self._source.capture_frame(
            rtc.VideoFrame(width, height, rtc.VideoBufferType.RGBA, rgba.tobytes())
        )

    async def aclose(self) -> None:
        if self._room.isconnected():
            await self._room.local_participant.unpublish_track(self._sid)
        await self._source.aclose()


class AudioSink:
    """One published audio track."""

    def __init__(
        self, source: rtc.AudioSource, sample_rate: int, channels: int
    ) -> None:
        self._source, self._sample_rate, self._channels = source, sample_rate, channels

    async def push(self, samples: np.ndarray) -> None:
        await self._source.capture_frame(
            rtc.AudioFrame(
                samples.tobytes(), self._sample_rate, self._channels, samples.shape[0]
            )
        )

    async def aclose(self) -> None:
        await self._source.aclose()


class DataSink:
    """One published data track. It is published only while this holds it."""

    def __init__(self, track: rtc.LocalDataTrack) -> None:
        self._track = track

    def push(self, packet: bytes) -> None:
        """Send one frame, or drop it: a data stream never queues."""
        try:
            self._track.try_push(rtc.DataTrackFrame(payload=packet))
        except rtc.PushFrameError:
            pass

    async def aclose(self) -> None:
        if self._track.is_published():
            await self._track.unpublish()


class Session:
    """One joined room, as the agent's publisher."""

    def __init__(self, room: rtc.Room, on_watchers: Callable[[int], None]) -> None:
        self._room = room
        self._gone: asyncio.Future[Gone] = asyncio.get_running_loop().create_future()

        def disconnected(reason: rtc.DisconnectReason.ValueType) -> None:
            if not self._gone.done():
                final = reason in _FINAL
                self._gone.set_result(
                    Gone(
                        reason=_FINAL[reason]
                        if final
                        else rtc.DisconnectReason.Name(reason),
                        final=final,
                        closed=reason == rtc.DisconnectReason.CLIENT_INITIATED,
                    )
                )

        def watchers(*_: Any) -> None:
            on_watchers(len(room.remote_participants))

        room.on("disconnected", disconnected)
        room.on("participant_connected", watchers)
        room.on("participant_disconnected", watchers)
        watchers()

    async def wait_gone(self) -> Gone:
        """Until the room went away; why."""
        return await self._gone

    async def video(
        self, key: str, width: int, height: int, max_framerate: float, max_bitrate: int
    ) -> VideoSink:
        source = rtc.VideoSource(width, height)
        track = rtc.LocalVideoTrack.create_video_track(key, source)
        options = rtc.TrackPublishOptions(
            source=rtc.TrackSource.SOURCE_CAMERA,
            video_encoding=rtc.VideoEncoding(
                max_framerate=max_framerate, max_bitrate=max_bitrate
            ),
        )
        publication = await self._room.local_participant.publish_track(track, options)
        return VideoSink(self._room, source, publication.sid, width, height)

    async def audio(self, key: str, sample_rate: int, channels: int) -> AudioSink:
        source = rtc.AudioSource(sample_rate, channels)
        track = rtc.LocalAudioTrack.create_audio_track(key, source)
        await self._room.local_participant.publish_track(
            track, rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
        )
        return AudioSink(source, sample_rate, channels)

    async def data(self, key: str) -> DataSink:
        return DataSink(await self._room.local_participant.publish_data_track(name=key))

    async def aclose(self) -> None:
        if self._room.isconnected():
            await self._room.disconnect()


class Viewing:
    """One joined room, as someone who watches."""

    def __init__(
        self, room: rtc.Room, published: asyncio.Queue[rtc.RemoteDataTrack]
    ) -> None:
        self._room = room
        self._published = published

    async def data(self, key: str) -> AsyncIterator[bytes]:
        """The frames of the data track named ``key``, newest only, until it is unpublished."""
        while True:
            track = await self._published.get()
            if track.info.name == key:
                break
        async for frame in track.subscribe(buffer_size=1):
            yield frame.payload

    async def aclose(self) -> None:
        if self._room.isconnected():
            await self._room.disconnect()


async def awatch(alias: Alias, credential: str) -> Viewing:
    """Join the room ``credential`` is for, to watch: nothing is subscribed until asked for."""
    room = rtc.Room()
    published: asyncio.Queue[rtc.RemoteDataTrack] = asyncio.Queue()
    room.on("data_track_published", published.put_nowait)
    url, options = await aroom_options(alias)
    options.auto_subscribe = False
    await room.connect(url, credential, options)
    return Viewing(room, published)


async def ajoin(
    alias: Alias, credential: str, on_watchers: Callable[[int], None]
) -> Session:
    """Join the room ``credential`` is for; ``on_watchers`` hears how many others are in it."""
    room = rtc.Room()
    url, options = await aroom_options(alias)
    await room.connect(url, credential, options)
    return Session(room, on_watchers)


async def aroom_options(alias: Alias) -> tuple[str, Any]:
    """The url to connect a ``livekit.rtc.Room`` to, and its options.

    ``room.connect(url, token, options)``: for a mesh alias the url is a local
    forward and the options relay all media through the mesh node the alias
    was resolved through; for any other alias they are the alias' url and the
    defaults.

    Raises:
        arkitekt_spec.declare.wiring.MeshError: If the alias is only reachable
            over the mesh but was not resolved through a mesh node this process
            runs.
    """
    if not alias.is_mesh():
        # LiveKit's SDK (rustls) reads its roots only from SSL_CERT_FILE: a pinned
        # SFU's hub certificate is added to them there.
        if alias.is_pinned():
            from arkitekt_spec.declare import tls

            tls.trust_natively(alias.certificates)
        return alias.to_ws_path(), rtc.RoomOptions()
    local = await alias.aforward()
    turn = await alias.aturn()
    options = rtc.RoomOptions(
        rtc_config=rtc.RtcConfiguration(
            ice_transport_type=rtc.IceTransportType.TRANSPORT_RELAY,
            ice_servers=[
                rtc.IceServer(
                    urls=list(turn.urls),
                    username=turn.username,
                    password=turn.credential,
                )
            ],
        )
    )
    # The forward carries the connection as it is: TLS to 127.0.0.1 would not
    # match the SFU's certificate, so mesh SFUs are reached in plain ws (the
    # mesh itself is encrypted).
    return f"ws://{local}{_path(alias)}", options


def _path(alias: Alias) -> str:
    path = (alias.path or "").strip("/")
    return f"/{path}" if path else ""
