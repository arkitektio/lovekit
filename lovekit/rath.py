from pydantic import Field
from rath.rath import Rath

from rath.links.auth import AuthTokenLink

from rath.links.compose import TypedComposedLink
from rath.links.dictinglink import DictingLink
from rath.links.shrink import ShrinkingLink
from rath.links.split import SplitLink


class LovekitLinkComposition(TypedComposedLink):
    shrinking: ShrinkingLink = Field(default_factory=ShrinkingLink)
    dicting: DictingLink = Field(default_factory=DictingLink)
    auth: AuthTokenLink
    split: SplitLink


class LovekitRath(Rath):
    """Lovekit Rath

    The GraphQL client for lovekit.

    It is the transport of a :class:`lovekit.lovekit.Lovekit` client; calls go
    through that client (``lovekit.aget_stream(id)``), which hands it this rath.
    """
