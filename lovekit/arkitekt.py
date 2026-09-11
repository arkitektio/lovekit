from graphql import OperationType
from fakts.contrib.rath.aiohttp import FaktsAIOHttpLink
from fakts.contrib.rath.auth import FaktsAuthLink
from fakts.contrib.rath.graphql_ws import FaktsGraphQLWSLink
from fakts import Fakts

from arkitekt.service_registry import (
    BaseArkitektService,
    Params,
    get_default_service_registry,
)
from fakts.models import Requirement
from lovekit.lovekit import Lovekit
from lovekit.rath import LovekitRath, LovekitLinkComposition
from rath.links.split import SplitLink


class LovekitService(BaseArkitektService):
    def get_service_name(self):
        return "lovekit"

    def build_service(
        self,
        fakts: Fakts,
        params: Params,
    ):
        return Lovekit(
            rath=LovekitRath(
                link=LovekitLinkComposition(
                    auth=FaktsAuthLink(fakts=fakts),
                    split=SplitLink(
                        left=FaktsAIOHttpLink(
                            fakts_group="lovekit", fakts=fakts, endpoint_url="FAKE_URL"
                        ),
                        right=FaktsGraphQLWSLink(
                            fakts_group="lovekit",
                            fakts=fakts,
                            ws_endpoint_url="FAKE_URL",
                        ),
                        split=lambda o: o.node.operation != OperationType.SUBSCRIPTION,
                    ),
                )
            )
        )

    def get_requirements(self):
        return [
            Requirement(
                key="livekit",
                service="io.livekit.livekit",
                description="An instance of ArkitektNext Lok to authenticate the user",
            ),
            Requirement(
                key="lovekit",
                service="live.arkitekt.lovekit",
                description="An instance of ArkitektNext Lovekit to interact with the Lovekit service",
            ),
        ]


get_default_service_registry().register(LovekitService())
