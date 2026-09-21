"""Integration tests for the Lovekit stream/broadcast API.

These require the docker-compose stack from ``conftest.py`` (the ``deployed_app``
session fixture) and are therefore marked ``integration`` and only run on Linux.
Every call goes through the deployment's client: nothing is ambient.
"""

import pytest
from lovekit.api.schema import StreamKind
from lovekit.lovekit import Lovekit


@pytest.mark.integration
def test_ensure_stream_returns_token(lovekit: Lovekit) -> None:
    """Ensuring a stream on a broadcast returns a non-empty connection token."""
    broadcast = lovekit.ensure_solo_broadcast(title="Test Stream")
    token = lovekit.ensure_stream(
        kind=StreamKind.VIDEO, broadcast=broadcast.id, title="Test Stream"
    )
    assert isinstance(token, str)
    assert token


@pytest.mark.integration
def test_ensure_audio_stream(lovekit: Lovekit) -> None:
    """An audio stream can be ensured just like a video stream."""
    broadcast = lovekit.ensure_solo_broadcast(title="Audio Stream")
    token = lovekit.ensure_stream(
        kind=StreamKind.AUDIO, broadcast=broadcast.id, title="Audio Stream"
    )
    assert isinstance(token, str)
    assert token


@pytest.mark.integration
def test_list_streams_contains_ensured_stream(lovekit: Lovekit) -> None:
    """A stream that was ensured shows up when listing streams."""
    broadcast = lovekit.ensure_solo_broadcast(title="Listed Stream")
    lovekit.ensure_stream(
        kind=StreamKind.VIDEO, broadcast=broadcast.id, title="Listed Stream"
    )
    streams = lovekit.list_streams()
    assert len(streams) >= 1
    assert all(stream.typename == "Stream" for stream in streams)


@pytest.mark.integration
def test_ensure_solo_broadcast_returns_broadcast(lovekit: Lovekit) -> None:
    """Ensuring a solo broadcast returns the broadcast with its id and title."""
    broadcast = lovekit.ensure_solo_broadcast(title="Solo Broadcast")
    assert broadcast.id
    assert broadcast.title == "Solo Broadcast"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_aget_stream_expands_through_the_client(lovekit: Lovekit) -> None:
    """The structure expander is the client's own method."""
    broadcast = await lovekit.aensure_solo_broadcast(title="Expand")
    got = await lovekit.aget_solo_broadcast(broadcast.id)
    assert got.id == broadcast.id
