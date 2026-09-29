"""Connecting rooms to the media server: directly, or through the mesh."""

from types import SimpleNamespace

import pytest
from livekit import rtc

from arkitekt_spec.declare.wiring import MeshError
from fakts import Alias
from lovekit.livekit import aroom_options


class FakeNode:
    """The mesh node a resolved mesh alias carries (fakts tests the real one)."""

    def __init__(self):
        self.forwarded = []

    async def forward(self, host, port):
        self.forwarded.append((host, port))
        return "127.0.0.1:5555"

    async def turn(self):
        return SimpleNamespace(
            urls=["turn:127.0.0.1:3478?transport=udp"], username="u", credential="c"
        )


@pytest.mark.asyncio
async def test_a_direct_server_is_connected_as_is():
    alias = Alias(id="lk", host="livekit.example", port=7880, ssl=True)
    url, options = await aroom_options(alias)
    assert url == "wss://livekit.example:7880"
    assert options.rtc_config is None


@pytest.mark.asyncio
async def test_a_mesh_server_goes_through_the_forward_and_the_relay():
    node = FakeNode()
    alias = Alias(id="lk", host="100.64.0.7", port=7880, path="/rtc-base", kind="mesh")
    alias = alias.through_mesh("http://127.0.0.1:41234", node)
    url, options = await aroom_options(alias)
    assert url == "ws://127.0.0.1:5555/rtc-base"
    assert node.forwarded == [("100.64.0.7", 7880)]
    config = options.rtc_config
    assert config.ice_transport_type == rtc.IceTransportType.TRANSPORT_RELAY
    (server,) = config.ice_servers
    assert list(server.urls) == ["turn:127.0.0.1:3478?transport=udp"]
    assert (server.username, server.password) == ("u", "c")


@pytest.mark.asyncio
async def test_a_mesh_server_needs_a_mesh_node():
    with pytest.raises(MeshError):
        await aroom_options(Alias(id="lk", host="100.64.0.7", kind="mesh"))
