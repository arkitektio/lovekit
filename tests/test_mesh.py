"""A data stream over the mesh: the agent and whoever watches reach a LiveKit that is on the mesh alone.

Needs the mesh lab with its LiveKit (arkitekt-mesh ``testing/mesh-lab``)::

    ./lab.sh up && ./lab.sh livekit && eval "$(./lab.sh env)"

and is skipped without it. lovekit itself is not in the lab: the client under test gets its
declaration and its connection from a stand-in that signs with the lab LiveKit's keys. What
is real is everything a mesh changes: two mesh nodes, signaling through a node's forward,
and all media through its TURN relay, to a server that offers candidates on the mesh only.
"""

import asyncio
import os
from collections.abc import Iterable
from pathlib import Path

import numpy as np
import pytest
from fakts import Alias
from livekit import api, rtc

from lovekit import Axis, AxisType, DataStream, frames
from lovekit.api.schema import Connection, Stream, StreamDeclarationInput, Transport
from lovekit.lovekit import Lovekit
from lovekit.transports.livekit import aroom_options

LAB = {
    name: os.environ.get(f"ARKITEKT_TEST_{name}")
    for name in ("MESH_URL", "MESH_KEY", "LIVEKIT_HOST", "LIVEKIT_KEY", "LIVEKIT_SECRET")
}
pytestmark = [
    pytest.mark.mesh,
    pytest.mark.skipif(not all(LAB.values()), reason="the mesh lab with LiveKit is not up (lab.sh up && lab.sh livekit)"),
]

ROOM = f"agent-mesh-{os.getpid()}"


def _token(identity: str, publish: bool) -> str:
    grants = api.VideoGrants(room_join=True, room=ROOM, can_publish=publish, can_subscribe=True, can_publish_data=publish)
    return api.AccessToken(LAB["LIVEKIT_KEY"], LAB["LIVEKIT_SECRET"]).with_identity(identity).with_grants(grants).to_jwt()


class LabLovekit(Lovekit):
    """lovekit's answers, signed for the lab's LiveKit."""

    async def adeclare_streams(self, streams: Iterable[StreamDeclarationInput]) -> tuple[Stream, ...]:
        return tuple(
            Stream.model_validate({"id": str(index), "key": stream.key, "title": stream.title, "kind": stream.kind, "agent": {"id": "1", "roomName": ROOM}})
            for index, stream in enumerate(streams, start=1)
        )

    async def apublisher_connection(self) -> Connection:
        return Connection(transport=Transport.LIVEKIT, credential=_token("agent-1", publish=True))


async def _on_the_mesh(statedir: Path, name: str) -> tuple[object, Alias]:
    """A mesh node of this process, and the lab's LiveKit as an alias resolved through it."""
    from arkitekt_mesh import Node

    node = await Node.start(str(statedir), f"t-lk-{name}-{os.getpid()}", control_url=LAB["MESH_URL"], auth_key=LAB["MESH_KEY"])
    alias = Alias(id="livekit", host=LAB["LIVEKIT_HOST"], port=7880, ssl=False, kind="mesh")
    return node, alias.through_mesh(node.proxy_url, node)


async def test_a_data_stream_reaches_who_watches_it_over_the_mesh(tmp_path: Path) -> None:
    pytest.importorskip("arkitekt_mesh")
    spectrum = DataStream("spectrum", dtype="float16", shape=(512,), axes=[Axis("wavelength", AxisType.SPECTRUM)])
    values = np.linspace(0, 1, 512, dtype=np.float16)

    agent_node, agent_alias = await _on_the_mesh(tmp_path / "agent", "agent")
    viewer_node, viewer_alias = await _on_the_mesh(tmp_path / "viewer", "viewer")
    room = rtc.Room()
    try:
        async with LabLovekit.model_construct(livekit=agent_alias).publish([spectrum]) as live:
            await live.wait_connected(timeout=60)
            feed = live.data("spectrum")
            await feed.send(values)

            # The viewer is its own node: relay-only through its TURN, as the agent is through its.
            url, options = await aroom_options(viewer_alias)
            assert url.startswith("ws://127.0.0.1:")
            assert options.rtc_config.ice_transport_type == rtc.IceTransportType.TRANSPORT_RELAY
            published: asyncio.Queue[rtc.RemoteDataTrack] = asyncio.Queue()
            room.on("data_track_published", published.put_nowait)
            await asyncio.wait_for(room.connect(url, _token("viewer-1", publish=False), options), 60)

            track = await asyncio.wait_for(published.get(), 30)
            await asyncio.wait_for(feed.wait_watched(), 30)
            packet = await asyncio.wait_for(anext(aiter(track.subscribe())), 30)
            frame = frames.decode(packet.payload, "float16", (512,))
            assert frame.sequence == 1 and (frame.values == values).all()
    finally:
        await room.disconnect()
        agent_node.close()
        viewer_node.close()
