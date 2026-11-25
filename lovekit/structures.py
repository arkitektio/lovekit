"""The types lovekit sends by id, each expanded by the ``Lovekit`` client.

Imported by ``lovekit/__init__``: an app using ``Lovekit`` takes every one of them.
"""

from arkitekt_spec.declare.structures.declare import structure
from arkitekt_spec.declare.widgets import SearchWidget

from lovekit.api.schema import Agent, SearchAgentsQuery, SearchStreamsQuery, Stream
from lovekit.lovekit import Lovekit


def _search(query: object) -> SearchWidget:
    """The widget that picks one of these out of the deployment."""
    return SearchWidget(query=query.Meta.document, ward="lovekit")  # type: ignore[attr-defined]


@structure("@lovekit/stream", widget=_search(SearchStreamsQuery))
async def expand_stream(id: str, lovekit: Lovekit) -> Stream:
    """A stream an agent offers, by id."""
    return await lovekit.aget_stream(id)


@structure("@lovekit/agent", widget=_search(SearchAgentsQuery))
async def expand_agent(id: str, lovekit: Lovekit) -> Agent:
    """An agent that offers streams, by id."""
    return await lovekit.aget_agent(id)
