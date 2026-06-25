"""Integration tests for the Lovekit stream/broadcast API.

These require the docker-compose stack from ``conftest.py`` (the ``deployed_app``
session fixture) and are therefore marked ``integration`` and only run on Linux.
"""

import pytest
from lovekit.api.schema import (
    StreamKind,
    ensure_stream,
    ensure_solo_broadcast,
    list_streams,
)
from .conftest import DeployedLovekit


@pytest.mark.integration
def test_ensure_stream_returns_token(deployed_app: DeployedLovekit) -> None:
    """Ensuring a stream on a broadcast returns a non-empty connection token."""
    broadcast = ensure_solo_broadcast(title="Test Stream")
    token = ensure_stream(
        kind=StreamKind.VIDEO, broadcast=broadcast.id, title="Test Stream"
    )
    assert isinstance(token, str)
    assert token


@pytest.mark.integration
def test_ensure_audio_stream(deployed_app: DeployedLovekit) -> None:
    """An audio stream can be ensured just like a video stream."""
    broadcast = ensure_solo_broadcast(title="Audio Stream")
    token = ensure_stream(
        kind=StreamKind.AUDIO, broadcast=broadcast.id, title="Audio Stream"
    )
    assert isinstance(token, str)
    assert token


@pytest.mark.integration
def test_list_streams_contains_ensured_stream(deployed_app: DeployedLovekit) -> None:
    """A stream that was ensured shows up when listing streams."""
    broadcast = ensure_solo_broadcast(title="Listed Stream")
    ensure_stream(kind=StreamKind.VIDEO, broadcast=broadcast.id, title="Listed Stream")
    streams = list_streams()
    assert len(streams) >= 1
    assert all(stream.typename == "Stream" for stream in streams)


@pytest.mark.integration
def test_ensure_solo_broadcast_returns_broadcast(deployed_app: DeployedLovekit) -> None:
    """Ensuring a solo broadcast returns the broadcast with its id and title."""
    broadcast = ensure_solo_broadcast(title="Solo Broadcast")
    assert broadcast.id
    assert broadcast.title == "Solo Broadcast"
