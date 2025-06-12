from rekuest_next.structures.default import get_default_structure_registry, id_shrink
from rekuest_next.widgets import SearchWidget
from lovekit.api.schema import (
    Stream,
    aget_stream,
    SearchStreamsQuery,
)

structure_reg = get_default_structure_registry()
structure_reg.register_as_structure(
    Stream,
    identifier="@lovekit/stream",
    aexpand=aget_stream,
    ashrink=id_shrink,
    default_widget=SearchWidget(query=SearchStreamsQuery.Meta.document, ward="lovekit"),
)
