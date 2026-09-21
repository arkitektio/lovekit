"""The lovekit service of an arkitekt app, and the types it sends by id.

Declared on one registry: the service first, then the structures whose expanders
ask for the client it returns. An app takes all of it in with
``App(services=[lovekit_service])``.
"""

from typing import Annotated

from fakts import Alias, Require, TokenLoader
from fakts.contrib.rath.auth import FaktsAuthLink
from graphql import OperationType
from rath.links.aiohttp import AIOHttpLink
from rath.links.graphql_ws import GraphQLWSLink
from rath.links.split import SplitLink

from rekuest.app import AppRegistry
from rekuest.widgets import SearchWidget

from lovekit.api.schema import (
    SearchSoloBroadcastQuery,
    SearchStreamsQuery,
    SoloBroadcast,
    Stream,
)
from lovekit.lovekit import Lovekit
from lovekit.rath import LovekitLinkComposition, LovekitRath


registry = AppRegistry()
"""What lovekit brings to an app: its service, and the types it can send by id."""


@registry.service()
def lovekit(
    lovekit: Annotated[
        Alias,
        Require("live.arkitekt.lovekit", "Where rooms and their tokens are managed"),
    ],
    livekit: Annotated[  # noqa: ARG001 -- declared, not dialled; see below
        Alias,
        Require("io.livekit.livekit", "The media server rooms are hosted on"),
    ],
    tokens: TokenLoader,
) -> Lovekit:
    """Lovekit: live audio and video rooms.

    ``livekit`` is declared but never dialled from here: the media server is
    reached by the livekit SDK with a token this service hands out, not over
    GraphQL. It stays a requirement because a deployment still has to compose
    one -- and now the manifest says so in the same place a client would.
    """
    return Lovekit(
        rath=LovekitRath(
            link=LovekitLinkComposition(
                auth=FaktsAuthLink(token_loader=tokens),
                split=SplitLink(
                    left=AIOHttpLink(endpoint_url=lovekit.to_http_path("graphql")),
                    right=GraphQLWSLink(ws_endpoint_url=lovekit.to_ws_path("graphql")),
                    split=lambda o: o.node.operation != OperationType.SUBSCRIPTION,
                ),
            )
        )
    )


def _search(query: object) -> SearchWidget:
    """The widget that picks one of these out of the deployment."""
    return SearchWidget(query=query.Meta.document, ward="lovekit")  # type: ignore[attr-defined]


@registry.structure("@lovekit/stream", widget=_search(SearchStreamsQuery))
async def expand_stream(id: str, lovekit: Lovekit) -> Stream:
    """A stream, by id."""
    return await lovekit.aget_stream(id)


@registry.structure("@lovekit/solo_broadcast", widget=_search(SearchSoloBroadcastQuery)
)
async def expand_solo_broadcast(id: str, lovekit: Lovekit) -> SoloBroadcast:
    """A solo broadcast, by id."""
    return await lovekit.aget_solo_broadcast(id)
