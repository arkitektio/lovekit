from arkitekt_next.base_models import Manifest
from koil.composition.base import KoiledModel
from herre import Herre
from fakts import Fakts

from arkitekt_next.service_registry import Params
from arkitekt_next.base_models import Requirement


def init_services(service_builder_registry):

    class ArkitektNextLovekit(KoiledModel):
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            pass

    def build_arkitekt_lovekit(
        fakts: Fakts, herre: Herre, params: Params, manifest: Manifest
    ):
        return ArkitektNextLovekit()

    service_builder_registry.register(
        "livekit",
        build_arkitekt_lovekit,
        Requirement(
            key="livekit",
            service="io.livekit.livekit",
            description="An instance of ArkitektNext Lok to authenticate the user",
        ),
    )
