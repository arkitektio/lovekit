"""Connecting rooms to the media server: directly, or through the mesh."""

from typing import TYPE_CHECKING

import pytest
from arkitekt_spec.declare.wiring import MeshError, TurnInfo
from fakts import Alias
from livekit import rtc

from lovekit.transports.livekit import aroom_options


class FakeNode:
    """The mesh node a resolved mesh alias carries (fakts tests the real one)."""

    def __init__(self) -> None:
        self.forwarded: list[tuple[str, int]] = []

    async def forward(self, host: str, port: int) -> str:
        self.forwarded.append((host, port))
        return "127.0.0.1:5555"

    async def turn(self) -> TurnInfo:
        return TurnInfo(
            urls=["turn:127.0.0.1:3478?transport=udp"], username="u", credential="c"
        )


@pytest.mark.asyncio
async def test_a_direct_server_is_connected_as_is() -> None:
    alias = Alias(id="lk", host="livekit.example", port=7880, ssl=True)
    url, options = await aroom_options(alias)
    assert url == "wss://livekit.example:7880"
    assert options.rtc_config is None


@pytest.mark.asyncio
async def test_a_mesh_server_goes_through_the_forward_and_the_relay() -> None:
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
async def test_a_mesh_server_needs_a_mesh_node() -> None:
    with pytest.raises(MeshError):
        await aroom_options(Alias(id="lk", host="100.64.0.7", kind="mesh"))


if TYPE_CHECKING:
    from livekit import rtc


def _stats(
    candidate_type: str, protocol: str, url: str = "", rtt: float = 0.037
) -> "rtc.RtcStats":
    from livekit import rtc
    from livekit.rtc._proto import stats_pb2 as s

    return rtc.RtcStats(
        publisher_stats=[
            s.RtcStats(
                transport=s.RtcStats.Transport(
                    rtc=s.RtcStatsData(id="T", timestamp=1),
                    transport=s.TransportStats(selected_candidate_pair_id="P"),
                )
            ),
            s.RtcStats(
                candidate_pair=s.RtcStats.CandidatePair(
                    rtc=s.RtcStatsData(id="P", timestamp=1),
                    candidate_pair=s.CandidatePairStats(
                        local_candidate_id="L",
                        current_round_trip_time=rtt,
                        nominated=True,
                    ),
                )
            ),
            s.RtcStats(
                local_candidate=s.RtcStats.LocalCandidate(
                    rtc=s.RtcStatsData(id="L", timestamp=1),
                    candidate=s.IceCandidateStats(
                        candidate_type=s.IceCandidateType.Value(candidate_type),
                        protocol=protocol,
                        url=url,
                    ),
                )
            ),
        ],
        subscriber_stats=[],
    )


def test_a_publisher_through_the_media_bridge_says_so_with_its_round_trip() -> None:
    from lovekit.transports.livekit import publisher_path

    assert publisher_path(
        _stats("RELAY", "udp", "turn:127.0.0.1:41234?transport=udp")
    ) == {
        "lovekit.rtt_ms": "37",
        "lovekit.transport": "udp",
        "lovekit.candidate": "relay",
        "lovekit.bridge": "1",
    }


def test_a_direct_publisher_is_no_bridge() -> None:
    from lovekit.transports.livekit import publisher_path

    path = publisher_path(_stats("HOST", "UDP", rtt=0.002))
    assert path["lovekit.candidate"] == "host"
    assert path["lovekit.transport"] == "udp"
    assert path["lovekit.bridge"] == "0"
    assert path["lovekit.rtt_ms"] == "2"


def test_no_pair_chosen_yet_reports_nothing() -> None:
    from livekit import rtc

    from lovekit.transports.livekit import publisher_path

    assert publisher_path(rtc.RtcStats(publisher_stats=[], subscriber_stats=[])) == {}


def test_a_ping_is_answered_with_what_was_sent() -> None:
    from livekit import rtc

    from lovekit.transports.livekit import answer_ping

    data = rtc.RpcInvocationData(
        request_id="r",
        caller_identity="user-3",
        payload="1732443600123",
        response_timeout=8.0,
    )
    assert answer_ping(data) == "1732443600123"


async def test_a_publishing_session_answers_pings() -> None:
    from lovekit.transports.livekit import PING_METHOD, Session, answer_ping

    registered: dict[str, object] = {}

    class FakeParticipant:
        def register_rpc_method(self, method: str, handler: object) -> None:
            registered[method] = handler

    class FakeRoom:
        local_participant = FakeParticipant()
        remote_participants: dict[str, object] = {}

        def on(self, *_: object) -> None:
            pass

        def isconnected(self) -> bool:
            return False

    session = Session(FakeRoom(), lambda _: None)  # type: ignore[arg-type]
    assert registered == {PING_METHOD: answer_ping}
    await session.aclose()
