"""Watching a stream another app publishes: its frames, as they come.

::

    async with lovekit.watch(stream) as frames:
        async for frame in frames:
            plot(frame.values)        # an array as the stream declared it

Only a data stream is watched this way; video and audio are for a viewer. Like the
stream itself, watching holds one value: a reader slower than the stream skips frames. The
frames end when the publisher takes the stream away or the connection drops; watch again
to follow a stream that comes back.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from lovekit import frames
from lovekit.api.schema import Stream, StreamKind, Transport

if TYPE_CHECKING:
    from lovekit.lovekit import Lovekit


@asynccontextmanager
async def watch(lovekit: Lovekit, stream: Stream) -> AsyncIterator[AsyncIterator[frames.Frame]]:
    """The frames of ``stream``, for as long as the block is open."""
    format = stream.format
    if stream.kind != StreamKind.DATA or format is None:
        raise TypeError(f"{stream.key} is a {stream.kind} stream: only a data stream is watched as frames")
    connection = await lovekit.awatch_stream(stream.id)
    if connection.transport != Transport.LIVEKIT:
        raise RuntimeError(f"lovekit hands out a {connection.transport} connection, which this lovekit client does not speak")
    if lovekit.livekit is None:
        raise RuntimeError("this lovekit client was built without the livekit alias")
    from lovekit.transports import livekit

    viewing = await livekit.awatch(lovekit.livekit, connection.credential)

    async def decoded() -> AsyncIterator[frames.Frame]:
        async for packet in viewing.data(stream.key):
            yield frames.decode(packet, format.dtype, format.shape)

    try:
        yield decoded()
    finally:
        await viewing.aclose()
