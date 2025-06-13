from rekuest_next.structures.default import get_default_structure_registry, id_shrink
from rekuest_next.widgets import SearchWidget
from lovekit.api.schema import (
    SoloBroadcast,
    Stream,
    aget_stream,
    SearchStreamsQuery,
    SearchSoloBroadcastQuery,
    aget_solo_broadcast,
)

structure_reg = get_default_structure_registry()
structure_reg.register_as_structure(
    Stream,
    identifier="@lovekit/stream",
    aexpand=aget_stream,
    ashrink=id_shrink,
    default_widget=SearchWidget(query=SearchStreamsQuery.Meta.document, ward="lovekit"),
)


structure_reg.register_as_structure(
    SoloBroadcast,
    identifier="@lovekit/solo_broadcast",
    aexpand=aget_solo_broadcast,
    ashrink=id_shrink,
    default_widget=SearchWidget(
        query=SearchSoloBroadcastQuery.Meta.document, ward="lovekit"
    ),
)
