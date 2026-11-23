"""An agent's streams, end to end: declared through the client, published into real LiveKit.

These require the docker-compose stack from ``conftest.py`` (the ``deployed_app`` session
fixture) and are therefore marked ``integration``. Frames go into the deployment's LiveKit
server, and whether a stream is live is read back through lovekit, the way an app sees it.
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

import numpy as np
import pytest
from livekit import api
from livekit.protocol.room import (
    DeleteRoomRequest,
    ListParticipantsRequest,
    RoomParticipantIdentity,
)

from lovekit import AudioStream, Axis, AxisType, Calibration, DataStream, VideoStream
from lovekit.api.schema import StreamDeclarationInput, StreamKind, Transport
from lovekit.lovekit import Lovekit
from tests.conftest import LIVEKIT_KEY, LIVEKIT_SECRET

pytestmark = [pytest.mark.integration]

T = TypeVar("T")

FRAME = np.zeros((32, 48, 4), dtype=np.uint8)


async def _eventually(
    read: Callable[[], Awaitable[T]], expected: T, timeout: float = 15.0
) -> T:
    """``read()`` once it returns ``expected``, or what it returns at the deadline."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while True:
        value = await read()
        if value == expected or loop.time() > deadline:
            return value
        await asyncio.sleep(0.25)


def _livekit(agent: Lovekit) -> api.LiveKitAPI:
    assert agent.livekit is not None
    return api.LiveKitAPI(
        f"http://{agent.livekit.host}:{agent.livekit.port}", LIVEKIT_KEY, LIVEKIT_SECRET
    )


async def _live(lovekit: Lovekit, stream_id: str) -> bool:
    return (await lovekit.ais_stream_live(stream_id)).live


async def _joins(live) -> int:
    return live.joins


async def test_declaring_without_publishing_offers_the_streams(
    lovekit: Lovekit,
) -> None:
    streams = await lovekit.adeclare_streams(
        [StreamDeclarationInput(key="idle", title="Idle", kind=StreamKind.VIDEO)]
    )
    assert [(s.key, s.title, s.kind) for s in streams] == [
        ("idle", "Idle", StreamKind.VIDEO)
    ]
    assert (await lovekit.ais_stream_live(streams[0].id)).live is False
    assert (await lovekit.aget_stream(streams[0].id)) == streams[0]
    agent = await lovekit.aget_agent(streams[0].agent.id)
    assert [s.key for s in agent.streams] == ["idle"]
    assert (await lovekit.apublisher_connection()).transport == Transport.LIVEKIT


async def test_a_published_stream_is_live_and_comes_back_with_its_id(
    agent: Lovekit,
) -> None:
    declared = [VideoStream("camera", title="Camera"), AudioStream("microphone")]
    async with agent.publish(declared) as live:
        assert [(s.key, s.kind) for s in live.streams] == [
            ("camera", StreamKind.VIDEO),
            ("microphone", StreamKind.AUDIO),
        ]
        camera = live.streams[0]
        await live.wait_connected(timeout=20)
        await live.video("camera").send(FRAME)
        assert await _eventually(lambda: _live(agent, camera.id), True) is True
        first_ids = [s.id for s in live.streams]
    assert await _eventually(lambda: _live(agent, camera.id), False) is False

    # The app starts again: the same streams, the same ids.
    async with agent.publish(declared) as again:
        assert [s.id for s in again.streams] == first_ids


def _spectrum(max_rate: float = 30.0) -> DataStream:
    return DataStream(
        "spectrum",
        dtype="float16",
        shape=(512,),
        axes=[Axis("wavelength", AxisType.SPECTRUM)],
        calibration=[Calibration("wavelength", unit="nm", scale=0.78, offset=400.0)],
        unit="counts",
        max_rate=max_rate,
    )


async def test_a_data_stream_reaches_who_watches_it(agent: Lovekit) -> None:
    values = np.linspace(0, 1, 512, dtype=np.float16)
    async with agent.publish([_spectrum()]) as live:
        [stream] = live.streams
        assert stream.kind == StreamKind.DATA
        assert stream.format is not None and (
            stream.format.dtype,
            stream.format.shape,
        ) == ("float16", (512,))
        await live.wait_connected(timeout=20)
        feed = live.data("spectrum")
        assert feed.watched is False
        await feed.send(values)
        assert await _eventually(lambda: _live(agent, stream.id), True) is True

        async with agent.watch(stream) as received:
            await asyncio.wait_for(feed.wait_watched(), 15)
            # Nothing new is sent: the late viewer gets the last frame, sent again.
            frame = await asyncio.wait_for(anext(received), 15)
            assert frame.sequence == 1 and (frame.values == values).all()

        # The viewer left: an app need not measure for nobody.
        async def watched() -> bool:
            return feed.watched

        assert await _eventually(watched, False) is False


async def test_a_data_stream_holds_one_value(agent: Lovekit) -> None:
    """Sent faster than its rate, a stream skips: the value that waits is replaced, never queued."""
    async with agent.publish([_spectrum(max_rate=2.0)]) as live:
        [stream] = live.streams
        await live.wait_connected(timeout=20)
        feed = live.data("spectrum")
        await feed.send(np.zeros(512, dtype=np.float16))
        async with agent.watch(stream) as received:
            assert (await asyncio.wait_for(anext(received), 15)).sequence == 1

            for level in (2.0, 3.0, 4.0):
                await feed.send(np.full(512, level, dtype=np.float16))
            seen: list[tuple[int, float]] = []
            while not seen or seen[-1][0] != 4:
                frame = await asyncio.wait_for(anext(received), 15)
                seen.append((frame.sequence, float(frame.values[0])))
            # The last one arrives, as it was sent. The one before it waited and was replaced:
            # whether the second went out at once or waited too depends on when the first did.
            assert seen[-1] == (4, 4.0)
            assert 3 not in [sequence for sequence, _ in seen]


async def test_a_data_stream_comes_back_with_its_last_value(agent: Lovekit) -> None:
    values = np.arange(512, dtype=np.float16)
    async with agent.publish([_spectrum()]) as live:
        [stream] = live.streams
        await live.wait_connected(timeout=20)
        await live.data("spectrum").send(values)
        assert await _eventually(lambda: _live(agent, stream.id), True) is True

        # The room goes away under the agent: joined again, the track is there again.
        client = _livekit(agent)
        try:
            await client.room.delete_room(
                DeleteRoomRequest(room=stream.agent.room_name)
            )
        finally:
            await client.aclose()
        assert await _eventually(lambda: _joins(live), 2, timeout=30) == 2
        assert await _eventually(lambda: _live(agent, stream.id), True) is True

        # Without the app sending anything new.
        async with agent.watch(stream) as received:
            frame = await asyncio.wait_for(anext(received), 15)
            assert frame.sequence == 1 and (frame.values == values).all()


async def test_a_track_follows_the_frame_size(agent: Lovekit) -> None:
    async with agent.publish([VideoStream("resizing")]) as live:
        await live.wait_connected(timeout=20)
        await live.video("resizing").send(FRAME)
        await live.video("resizing").send(np.zeros((64, 64, 4), dtype=np.uint8))
        assert await _eventually(lambda: _live(agent, live.streams[0].id), True) is True


async def test_a_dropped_room_is_joined_again(agent: Lovekit) -> None:
    async with agent.publish([VideoStream("camera")]) as live:
        await live.wait_connected(timeout=20)
        await live.video("camera").send(FRAME)
        stream = live.streams[0]
        assert await _eventually(lambda: _live(agent, stream.id), True) is True

        # The room goes away under the agent (a server restart, an operator): it comes back.
        client = _livekit(agent)
        try:
            await client.room.delete_room(
                DeleteRoomRequest(room=stream.agent.room_name)
            )
        finally:
            await client.aclose()
        assert live.joins == 1
        assert await _eventually(lambda: _joins(live), 2, timeout=30) == 2
        assert live.connected.is_set() and not live.stopped.is_set()
        # Published again with its last frame, without the app sending a new one.
        assert await _eventually(lambda: _live(agent, stream.id), True) is True


async def test_a_newer_process_of_the_agent_takes_over_and_the_old_one_stops(
    agent: Lovekit,
) -> None:
    newer = Lovekit(rath=agent.rath, livekit=agent.livekit)
    async with agent.publish([VideoStream("camera")]) as old:
        await old.wait_connected(timeout=20)
        await old.video("camera").send(FRAME)

        async with newer.publish([VideoStream("camera")]) as new:
            await new.wait_connected(timeout=20)
            await new.video("camera").send(FRAME)

            assert (
                await asyncio.wait_for(old.wait_stopped(), 15)
                == "replaced by a newer connection of this agent"
            )
            # It does not fight back: after a while the newer process still holds the room.
            await asyncio.sleep(3)
            assert new.connected.is_set() and not new.stopped.is_set()
            client = _livekit(agent)
            try:
                room = new.streams[0].agent.room_name
                participants = (
                    await client.room.list_participants(
                        ListParticipantsRequest(room=room)
                    )
                ).participants
            finally:
                await client.aclose()
            assert [(p.identity, [t.name for t in p.tracks]) for p in participants] == [
                (f"agent-{new.streams[0].agent.id}", ["camera"])
            ]
            # Sending to the stopped one does nothing.
            await old.video("camera").send(FRAME)


async def test_a_removed_agent_stops(agent: Lovekit) -> None:
    async with agent.publish([VideoStream("camera")]) as live:
        await live.wait_connected(timeout=20)
        client = _livekit(agent)
        try:
            await client.room.remove_participant(
                RoomParticipantIdentity(
                    room=live.streams[0].agent.room_name,
                    identity=f"agent-{live.streams[0].agent.id}",
                )
            )
        finally:
            await client.aclose()
        assert (
            await asyncio.wait_for(live.wait_stopped(), 15) == "removed from the room"
        )


async def test_an_agent_publishes_once_at_a_time(agent: Lovekit) -> None:
    async with agent.publish([VideoStream("camera")]):
        with pytest.raises(RuntimeError):
            agent.publish([VideoStream("other")])
    # Closed, it may publish again.
    async with agent.publish([VideoStream("camera")]):
        pass


async def test_a_refused_declaration_raises_and_frees_the_client(
    agent: Lovekit,
) -> None:
    from rath.operation import GraphQLException

    with pytest.raises(GraphQLException):
        async with agent.publish([VideoStream(" ")]):
            pass
    # Nothing holds the client: it publishes what lovekit accepts.
    async with agent.publish([VideoStream("camera")]) as live:
        assert [s.key for s in live.streams] == ["camera"]


async def test_a_key_is_declared_once(agent: Lovekit) -> None:
    with pytest.raises(ValueError):
        agent.publish([VideoStream("camera"), AudioStream("camera")])
