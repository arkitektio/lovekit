from arkitekt_next.base_models import Manifest
from koil.composition.base import KoiledModel
from herre_next import Herre
from fakts_next import Fakts

from arkitekt_next.service_registry import BaseArkitektService, Params, get_default_service_registry
from arkitekt_next.base_models import Requirement


class LovekitService(BaseArkitektService):

    def get_service_name(self):
        return "lovekit"

    def build_service(
        self, fakts: Fakts, herre: Herre, params: Params, manifest: Manifest
    ):
        return None

    def get_requirements(self):
        return [
            Requirement(
                key="livekit",
                service="io.livekit.livekit",
                description="An instance of ArkitektNext Lok to authenticate the user",
            )
        ]

    def get_graphql_schema(self):
        return ModuleNotFoundError


get_default_service_registry().register(LovekitService())
