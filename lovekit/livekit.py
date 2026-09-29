"""Connecting to the LiveKit media server, also when it is only on the mesh.

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

from typing import Any, Optional

from fakts import Alias


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
    from livekit import rtc

    if not alias.is_mesh():
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


async def aconnect_room(alias: Alias, token: str, room: Optional[Any] = None) -> Any:
    """Connect ``room`` (a new ``livekit.rtc.Room`` by default) with
    :func:`aroom_options`, and return it."""
    from livekit import rtc

    room = room or rtc.Room()
    url, options = await aroom_options(alias)
    await room.connect(url, token, options)
    return room
