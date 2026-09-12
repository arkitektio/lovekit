from enum import Enum
from lovekit.funcs import aexecute, execute
from lovekit.rath import LovekitRath
from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from rath.scalars import ID, IDCoercible
from typing import Annotated, Any, Literal


class GraphQLDefault:
    """Records a GraphQL field schema default value. The client omits the field so the server applies its own default; this preserves the value for introspection."""

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "GraphQLDefault(" + repr(self.value) + ")"


class UnsetType:
    """Sentinel for arguments the caller did not provide. Such fields are omitted on serialization so the GraphQL server applies its own default."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self):
        return "UNSET"

    def __bool__(self):
        return False


UNSET = UnsetType()


class StreamKind(str, Enum):
    """The state of a dask cluster"""

    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    __str__ = str.__str__


class CollaborativeBroadcastFilter(BaseModel):
    """Filter for Solo Broadcasts"""

    ids: tuple[ID, ...] | None = None
    search: str | None = None
    and_: "CollaborativeBroadcastFilter | None" = Field(
        validation_alias=AliasChoices("and_", "AND"),
        serialization_alias="AND",
        default=None,
    )
    or_: "CollaborativeBroadcastFilter | None" = Field(
        validation_alias=AliasChoices("or_", "OR"),
        serialization_alias="OR",
        default=None,
    )
    not_: "CollaborativeBroadcastFilter | None" = Field(
        validation_alias=AliasChoices("not_", "NOT"),
        serialization_alias="NOT",
        default=None,
    )
    distinct: bool | None = Field(
        validation_alias=AliasChoices("distinct", "DISTINCT"),
        serialization_alias="DISTINCT",
        default=None,
    )
    model_config = ConfigDict(frozen=True, extra="forbid")


class EnsureSoloBroadcastInput(BaseModel):
    """No documentation"""

    instance_id: str | None = Field(
        validation_alias=AliasChoices("instance_id", "instanceId"),
        serialization_alias="instanceId",
        default=None,
    )
    title: str | None = None
    model_config = ConfigDict(frozen=True, extra="forbid")


class EnsureStreamInput(BaseModel):
    """No documentation"""

    broadcast: ID | None = None
    kind: Annotated[StreamKind | None, GraphQLDefault("VIDEO")] = None
    "Default: VIDEO"
    title: str | None = None
    model_config = ConfigDict(frozen=True, extra="forbid")


class OffsetPaginationInput(BaseModel):
    """No documentation"""

    offset: Annotated[int | None, GraphQLDefault("0")] = None
    "Default: 0"
    limit: int | None = None
    model_config = ConfigDict(frozen=True, extra="forbid")


class SoloBroadcastFilter(BaseModel):
    """Filter for Solo Broadcasts"""

    ids: tuple[ID, ...] | None = None
    search: str | None = None
    and_: "SoloBroadcastFilter | None" = Field(
        validation_alias=AliasChoices("and_", "AND"),
        serialization_alias="AND",
        default=None,
    )
    or_: "SoloBroadcastFilter | None" = Field(
        validation_alias=AliasChoices("or_", "OR"),
        serialization_alias="OR",
        default=None,
    )
    not_: "SoloBroadcastFilter | None" = Field(
        validation_alias=AliasChoices("not_", "NOT"),
        serialization_alias="NOT",
        default=None,
    )
    distinct: bool | None = Field(
        validation_alias=AliasChoices("distinct", "DISTINCT"),
        serialization_alias="DISTINCT",
        default=None,
    )
    model_config = ConfigDict(frozen=True, extra="forbid")


class StreamFilter(BaseModel):
    """Filter for Streams"""

    ids: tuple[ID, ...] | None = None
    search: str | None = None
    and_: "StreamFilter | None" = Field(
        validation_alias=AliasChoices("and_", "AND"),
        serialization_alias="AND",
        default=None,
    )
    or_: "StreamFilter | None" = Field(
        validation_alias=AliasChoices("or_", "OR"),
        serialization_alias="OR",
        default=None,
    )
    not_: "StreamFilter | None" = Field(
        validation_alias=AliasChoices("not_", "NOT"),
        serialization_alias="NOT",
        default=None,
    )
    distinct: bool | None = Field(
        validation_alias=AliasChoices("distinct", "DISTINCT"),
        serialization_alias="DISTINCT",
        default=None,
    )
    model_config = ConfigDict(frozen=True, extra="forbid")


class Stream(BaseModel):
    """No documentation"""

    typename: Literal["Stream"] = Field(
        alias="__typename", default="Stream", exclude=True
    )
    id: ID
    model_config = ConfigDict(frozen=True)

    class Meta:
        """Meta class for Stream"""

        document = "fragment Stream on Stream {\n  id\n  __typename\n}"
        name = "Stream"
        type = "Stream"


class StreamerUser(BaseModel):
    """No documentation"""

    typename: Literal["User"] = Field(alias="__typename", default="User", exclude=True)
    sub: str
    model_config = ConfigDict(frozen=True)


class StreamerClient(BaseModel):
    """No documentation"""

    typename: Literal["Client"] = Field(
        alias="__typename", default="Client", exclude=True
    )
    client_id: str = Field(alias="clientId")
    model_config = ConfigDict(frozen=True)


class Streamer(BaseModel):
    """No documentation"""

    typename: Literal["Streamer"] = Field(
        alias="__typename", default="Streamer", exclude=True
    )
    user: StreamerUser
    client: StreamerClient
    model_config = ConfigDict(frozen=True)

    class Meta:
        """Meta class for Streamer"""

        document = "fragment Streamer on Streamer {\n  user {\n    sub\n    __typename\n  }\n  client {\n    clientId\n    __typename\n  }\n  __typename\n}"
        name = "Streamer"
        type = "Streamer"


class SoloBroadcast(BaseModel):
    """No documentation"""

    typename: Literal["SoloBroadcast"] = Field(
        alias="__typename", default="SoloBroadcast", exclude=True
    )
    id: ID
    title: str
    streamer: Streamer
    model_config = ConfigDict(frozen=True)

    class Meta:
        """Meta class for SoloBroadcast"""

        document = "fragment Streamer on Streamer {\n  user {\n    sub\n    __typename\n  }\n  client {\n    clientId\n    __typename\n  }\n  __typename\n}\n\nfragment SoloBroadcast on SoloBroadcast {\n  id\n  title\n  streamer {\n    ...Streamer\n    __typename\n  }\n  __typename\n}"
        name = "SoloBroadcast"
        type = "SoloBroadcast"


class CollaborativeBroadcast(BaseModel):
    """No documentation"""

    typename: Literal["CollaborativeBroadcast"] = Field(
        alias="__typename", default="CollaborativeBroadcast", exclude=True
    )
    id: ID
    title: str
    streamers: tuple[Streamer, ...]
    "The streamers that are collaborating on this broadcast."
    model_config = ConfigDict(frozen=True)

    class Meta:
        """Meta class for CollaborativeBroadcast"""

        document = "fragment Streamer on Streamer {\n  user {\n    sub\n    __typename\n  }\n  client {\n    clientId\n    __typename\n  }\n  __typename\n}\n\nfragment CollaborativeBroadcast on CollaborativeBroadcast {\n  id\n  title\n  streamers {\n    ...Streamer\n    __typename\n  }\n  __typename\n}"
        name = "CollaborativeBroadcast"
        type = "CollaborativeBroadcast"


class EnsureSoloBroadcastMutation(BaseModel):
    """No documentation found for this operation."""

    ensure_solo_broadcast: SoloBroadcast = Field(alias="ensureSoloBroadcast")
    "Create a solo broadcast"

    class Arguments(BaseModel):
        """Arguments for EnsureSoloBroadcast"""

        input: EnsureSoloBroadcastInput

    class Meta:
        """Meta class for EnsureSoloBroadcast"""

        document = "fragment Streamer on Streamer {\n  user {\n    sub\n    __typename\n  }\n  client {\n    clientId\n    __typename\n  }\n  __typename\n}\n\nfragment SoloBroadcast on SoloBroadcast {\n  id\n  title\n  streamer {\n    ...Streamer\n    __typename\n  }\n  __typename\n}\n\nmutation EnsureSoloBroadcast($input: EnsureSoloBroadcastInput!) {\n  ensureSoloBroadcast(input: $input) {\n    ...SoloBroadcast\n    __typename\n  }\n}"


class EnsureStreamMutation(BaseModel):
    """No documentation found for this operation."""

    ensure_stream: str = Field(alias="ensureStream")
    "Create a stream and return the token for it"

    class Arguments(BaseModel):
        """Arguments for EnsureStream"""

        input: EnsureStreamInput

    class Meta:
        """Meta class for EnsureStream"""

        document = "mutation EnsureStream($input: EnsureStreamInput!) {\n  ensureStream(input: $input)\n}"


class GetCollaborativeBroadcastQuery(BaseModel):
    """No documentation found for this operation."""

    collaborative_broadcast: CollaborativeBroadcast = Field(
        alias="collaborativeBroadcast"
    )
    "Get a collaborative broadcast by ID"

    class Arguments(BaseModel):
        """Arguments for GetCollaborativeBroadcast"""

        id: ID

    class Meta:
        """Meta class for GetCollaborativeBroadcast"""

        document = "fragment Streamer on Streamer {\n  user {\n    sub\n    __typename\n  }\n  client {\n    clientId\n    __typename\n  }\n  __typename\n}\n\nfragment CollaborativeBroadcast on CollaborativeBroadcast {\n  id\n  title\n  streamers {\n    ...Streamer\n    __typename\n  }\n  __typename\n}\n\nquery GetCollaborativeBroadcast($id: ID!) {\n  collaborativeBroadcast(id: $id) {\n    ...CollaborativeBroadcast\n    __typename\n  }\n}"


class SearchollaborativeBroadcastsQueryOptions(BaseModel):
    """No documentation"""

    typename: Literal["CollaborativeBroadcast"] = Field(
        alias="__typename", default="CollaborativeBroadcast", exclude=True
    )
    value: ID
    label: str
    model_config = ConfigDict(frozen=True)


class SearchollaborativeBroadcastsQuery(BaseModel):
    """No documentation found for this operation."""

    options: tuple[SearchollaborativeBroadcastsQueryOptions, ...]
    "Get all collaborative broadcasts"

    class Arguments(BaseModel):
        """Arguments for SearchollaborativeBroadcasts"""

        search: str | None = Field(default=None)
        values: list[ID] | None = Field(default=None)

    class Meta:
        """Meta class for SearchollaborativeBroadcasts"""

        document = "query SearchollaborativeBroadcasts($search: String, $values: [ID!]) {\n  options: collaborativeBroadcasts(\n    filters: {search: $search, ids: $values}\n    pagination: {limit: 10}\n  ) {\n    value: id\n    label: title\n    __typename\n  }\n}"


class ListCollaborativeBroadcastsQuery(BaseModel):
    """No documentation found for this operation."""

    collaborative_broadcasts: tuple[CollaborativeBroadcast, ...] = Field(
        alias="collaborativeBroadcasts"
    )
    "Get all collaborative broadcasts"

    class Arguments(BaseModel):
        """Arguments for ListCollaborativeBroadcasts"""

        filter: CollaborativeBroadcastFilter | None = Field(default=None)
        pagination: OffsetPaginationInput | None = Field(default=None)

    class Meta:
        """Meta class for ListCollaborativeBroadcasts"""

        document = "fragment Streamer on Streamer {\n  user {\n    sub\n    __typename\n  }\n  client {\n    clientId\n    __typename\n  }\n  __typename\n}\n\nfragment CollaborativeBroadcast on CollaborativeBroadcast {\n  id\n  title\n  streamers {\n    ...Streamer\n    __typename\n  }\n  __typename\n}\n\nquery ListCollaborativeBroadcasts($filter: CollaborativeBroadcastFilter, $pagination: OffsetPaginationInput) {\n  collaborativeBroadcasts(filters: $filter, pagination: $pagination) {\n    ...CollaborativeBroadcast\n    __typename\n  }\n}"


class GetSoloBroadcastQuery(BaseModel):
    """No documentation found for this operation."""

    solo_broadcast: SoloBroadcast = Field(alias="soloBroadcast")
    "Get a solo broadcast by ID"

    class Arguments(BaseModel):
        """Arguments for GetSoloBroadcast"""

        id: ID

    class Meta:
        """Meta class for GetSoloBroadcast"""

        document = "fragment Streamer on Streamer {\n  user {\n    sub\n    __typename\n  }\n  client {\n    clientId\n    __typename\n  }\n  __typename\n}\n\nfragment SoloBroadcast on SoloBroadcast {\n  id\n  title\n  streamer {\n    ...Streamer\n    __typename\n  }\n  __typename\n}\n\nquery GetSoloBroadcast($id: ID!) {\n  soloBroadcast(id: $id) {\n    ...SoloBroadcast\n    __typename\n  }\n}"


class SearchSoloBroadcastQueryOptions(BaseModel):
    """No documentation"""

    typename: Literal["SoloBroadcast"] = Field(
        alias="__typename", default="SoloBroadcast", exclude=True
    )
    value: ID
    label: str
    model_config = ConfigDict(frozen=True)


class SearchSoloBroadcastQuery(BaseModel):
    """No documentation found for this operation."""

    options: tuple[SearchSoloBroadcastQueryOptions, ...]
    "Get all solo broadcasts"

    class Arguments(BaseModel):
        """Arguments for SearchSoloBroadcast"""

        search: str | None = Field(default=None)
        values: list[ID] | None = Field(default=None)

    class Meta:
        """Meta class for SearchSoloBroadcast"""

        document = "query SearchSoloBroadcast($search: String, $values: [ID!]) {\n  options: soloBroadcasts(\n    filters: {search: $search, ids: $values}\n    pagination: {limit: 10}\n  ) {\n    value: id\n    label: title\n    __typename\n  }\n}"


class ListSoloBroadcastsQuery(BaseModel):
    """No documentation found for this operation."""

    solo_broadcasts: tuple[SoloBroadcast, ...] = Field(alias="soloBroadcasts")
    "Get all solo broadcasts"

    class Arguments(BaseModel):
        """Arguments for ListSoloBroadcasts"""

        filter: SoloBroadcastFilter | None = Field(default=None)
        pagination: OffsetPaginationInput | None = Field(default=None)

    class Meta:
        """Meta class for ListSoloBroadcasts"""

        document = "fragment Streamer on Streamer {\n  user {\n    sub\n    __typename\n  }\n  client {\n    clientId\n    __typename\n  }\n  __typename\n}\n\nfragment SoloBroadcast on SoloBroadcast {\n  id\n  title\n  streamer {\n    ...Streamer\n    __typename\n  }\n  __typename\n}\n\nquery ListSoloBroadcasts($filter: SoloBroadcastFilter, $pagination: OffsetPaginationInput) {\n  soloBroadcasts(filters: $filter, pagination: $pagination) {\n    ...SoloBroadcast\n    __typename\n  }\n}"


class GetStreamQuery(BaseModel):
    """No documentation found for this operation."""

    stream: Stream
    "Get a stream by ID"

    class Arguments(BaseModel):
        """Arguments for GetStream"""

        id: ID

    class Meta:
        """Meta class for GetStream"""

        document = "fragment Stream on Stream {\n  id\n  __typename\n}\n\nquery GetStream($id: ID!) {\n  stream(id: $id) {\n    ...Stream\n    __typename\n  }\n}"


class SearchStreamsQueryOptions(BaseModel):
    """No documentation"""

    typename: Literal["Stream"] = Field(
        alias="__typename", default="Stream", exclude=True
    )
    value: ID
    label: str
    model_config = ConfigDict(frozen=True)


class SearchStreamsQuery(BaseModel):
    """No documentation found for this operation."""

    options: tuple[SearchStreamsQueryOptions, ...]
    "Get a stream"

    class Arguments(BaseModel):
        """Arguments for SearchStreams"""

        search: str | None = Field(default=None)
        values: list[ID] | None = Field(default=None)

    class Meta:
        """Meta class for SearchStreams"""

        document = "query SearchStreams($search: String, $values: [ID!]) {\n  options: streams(\n    filters: {search: $search, ids: $values}\n    pagination: {limit: 10}\n  ) {\n    value: id\n    label: title\n    __typename\n  }\n}"


class ListStreamsQuery(BaseModel):
    """No documentation found for this operation."""

    streams: tuple[Stream, ...]
    "Get a stream"

    class Arguments(BaseModel):
        """Arguments for ListStreams"""

        filter: StreamFilter | None = Field(default=None)
        pagination: OffsetPaginationInput | None = Field(default=None)

    class Meta:
        """Meta class for ListStreams"""

        document = "fragment Stream on Stream {\n  id\n  __typename\n}\n\nquery ListStreams($filter: StreamFilter, $pagination: OffsetPaginationInput) {\n  streams(filters: $filter, pagination: $pagination) {\n    ...Stream\n    __typename\n  }\n}"


async def aensure_solo_broadcast(
    instance_id: str | None | UnsetType = UNSET,
    title: str | None | UnsetType = UNSET,
    rath: LovekitRath | None = None,
) -> SoloBroadcast:
    """EnsureSoloBroadcast

    Create a solo broadcast

    Args:
        instance_id: The `String` scalar type represents textual data, represented as UTF-8 character sequences. The String type is most often used by GraphQL to represent free-form human-readable text.
        title: The `String` scalar type represents textual data, represented as UTF-8 character sequences. The String type is most often used by GraphQL to represent free-form human-readable text.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        SoloBroadcast
    """
    variables: dict[str, Any] = {}
    _input: dict[str, Any] = {}
    if instance_id is not UNSET:
        _input["instanceId"] = instance_id
    if title is not UNSET:
        _input["title"] = title
    variables["input"] = _input
    return (
        await aexecute(EnsureSoloBroadcastMutation, variables, rath=rath)
    ).ensure_solo_broadcast


def ensure_solo_broadcast(
    instance_id: str | None | UnsetType = UNSET,
    title: str | None | UnsetType = UNSET,
    rath: LovekitRath | None = None,
) -> SoloBroadcast:
    """EnsureSoloBroadcast

    Create a solo broadcast

    Args:
        instance_id: The `String` scalar type represents textual data, represented as UTF-8 character sequences. The String type is most often used by GraphQL to represent free-form human-readable text.
        title: The `String` scalar type represents textual data, represented as UTF-8 character sequences. The String type is most often used by GraphQL to represent free-form human-readable text.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        SoloBroadcast
    """
    variables: dict[str, Any] = {}
    _input: dict[str, Any] = {}
    if instance_id is not UNSET:
        _input["instanceId"] = instance_id
    if title is not UNSET:
        _input["title"] = title
    variables["input"] = _input
    return execute(
        EnsureSoloBroadcastMutation, variables, rath=rath
    ).ensure_solo_broadcast


async def aensure_stream(
    kind: StreamKind,
    broadcast: IDCoercible | None | UnsetType = UNSET,
    title: str | None | UnsetType = UNSET,
    rath: LovekitRath | None = None,
) -> str:
    """EnsureStream

    Create a stream and return the token for it

    Args:
        broadcast: The `ID` scalar type represents a unique identifier, often used to refetch an object or as key for a cache. The ID type appears in a JSON response as a String; however, it is not intended to be human-readable. When expected as an input type, any string (such as `"4"`) or integer (such as `4`) input value will be accepted as an ID.
        kind: StreamKind (required)
        title: The `String` scalar type represents textual data, represented as UTF-8 character sequences. The String type is most often used by GraphQL to represent free-form human-readable text.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        str
    """
    variables: dict[str, Any] = {}
    _input: dict[str, Any] = {}
    if broadcast is not UNSET:
        _input["broadcast"] = broadcast
    _input["kind"] = kind
    if title is not UNSET:
        _input["title"] = title
    variables["input"] = _input
    return (await aexecute(EnsureStreamMutation, variables, rath=rath)).ensure_stream


def ensure_stream(
    kind: StreamKind,
    broadcast: IDCoercible | None | UnsetType = UNSET,
    title: str | None | UnsetType = UNSET,
    rath: LovekitRath | None = None,
) -> str:
    """EnsureStream

    Create a stream and return the token for it

    Args:
        broadcast: The `ID` scalar type represents a unique identifier, often used to refetch an object or as key for a cache. The ID type appears in a JSON response as a String; however, it is not intended to be human-readable. When expected as an input type, any string (such as `"4"`) or integer (such as `4`) input value will be accepted as an ID.
        kind: StreamKind (required)
        title: The `String` scalar type represents textual data, represented as UTF-8 character sequences. The String type is most often used by GraphQL to represent free-form human-readable text.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        str
    """
    variables: dict[str, Any] = {}
    _input: dict[str, Any] = {}
    if broadcast is not UNSET:
        _input["broadcast"] = broadcast
    _input["kind"] = kind
    if title is not UNSET:
        _input["title"] = title
    variables["input"] = _input
    return execute(EnsureStreamMutation, variables, rath=rath).ensure_stream


async def aget_collaborative_broadcast(
    id: IDCoercible, rath: LovekitRath | None = None
) -> CollaborativeBroadcast:
    """GetCollaborativeBroadcast

    Get a collaborative broadcast by ID

    Args:
        id (ID): No description
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        CollaborativeBroadcast
    """
    variables: dict[str, Any] = {}
    variables["id"] = id
    return (
        await aexecute(GetCollaborativeBroadcastQuery, variables, rath=rath)
    ).collaborative_broadcast


def get_collaborative_broadcast(
    id: IDCoercible, rath: LovekitRath | None = None
) -> CollaborativeBroadcast:
    """GetCollaborativeBroadcast

    Get a collaborative broadcast by ID

    Args:
        id (ID): No description
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        CollaborativeBroadcast
    """
    variables: dict[str, Any] = {}
    variables["id"] = id
    return execute(
        GetCollaborativeBroadcastQuery, variables, rath=rath
    ).collaborative_broadcast


async def asearchollaborative_broadcasts(
    search: str | None | UnsetType = UNSET,
    values: list[IDCoercible] | None | UnsetType = UNSET,
    rath: LovekitRath | None = None,
) -> tuple[SearchollaborativeBroadcastsQueryOptions, ...]:
    """SearchollaborativeBroadcasts

    Get all collaborative broadcasts

    Args:
        search (str | None, optional): No description.
        values (list[ID] | None, optional): No description.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        list[SearchollaborativeBroadcastsQueryCollaborativeBroadcasts]
    """
    variables: dict[str, Any] = {}
    if search is not UNSET:
        variables["search"] = search
    if values is not UNSET:
        variables["values"] = values
    return (
        await aexecute(SearchollaborativeBroadcastsQuery, variables, rath=rath)
    ).options


def searchollaborative_broadcasts(
    search: str | None | UnsetType = UNSET,
    values: list[IDCoercible] | None | UnsetType = UNSET,
    rath: LovekitRath | None = None,
) -> tuple[SearchollaborativeBroadcastsQueryOptions, ...]:
    """SearchollaborativeBroadcasts

    Get all collaborative broadcasts

    Args:
        search (str | None, optional): No description.
        values (list[ID] | None, optional): No description.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        list[SearchollaborativeBroadcastsQueryCollaborativeBroadcasts]
    """
    variables: dict[str, Any] = {}
    if search is not UNSET:
        variables["search"] = search
    if values is not UNSET:
        variables["values"] = values
    return execute(SearchollaborativeBroadcastsQuery, variables, rath=rath).options


async def alist_collaborative_broadcasts(
    filter: CollaborativeBroadcastFilter | None | UnsetType = UNSET,
    pagination: OffsetPaginationInput | None | UnsetType = UNSET,
    rath: LovekitRath | None = None,
) -> tuple[CollaborativeBroadcast, ...]:
    """ListCollaborativeBroadcasts

    Get all collaborative broadcasts

    Args:
        filter (CollaborativeBroadcastFilter | None, optional): No description.
        pagination (OffsetPaginationInput | None, optional): No description.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        list[CollaborativeBroadcast]
    """
    variables: dict[str, Any] = {}
    if filter is not UNSET:
        variables["filter"] = filter
    if pagination is not UNSET:
        variables["pagination"] = pagination
    return (
        await aexecute(ListCollaborativeBroadcastsQuery, variables, rath=rath)
    ).collaborative_broadcasts


def list_collaborative_broadcasts(
    filter: CollaborativeBroadcastFilter | None | UnsetType = UNSET,
    pagination: OffsetPaginationInput | None | UnsetType = UNSET,
    rath: LovekitRath | None = None,
) -> tuple[CollaborativeBroadcast, ...]:
    """ListCollaborativeBroadcasts

    Get all collaborative broadcasts

    Args:
        filter (CollaborativeBroadcastFilter | None, optional): No description.
        pagination (OffsetPaginationInput | None, optional): No description.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        list[CollaborativeBroadcast]
    """
    variables: dict[str, Any] = {}
    if filter is not UNSET:
        variables["filter"] = filter
    if pagination is not UNSET:
        variables["pagination"] = pagination
    return execute(
        ListCollaborativeBroadcastsQuery, variables, rath=rath
    ).collaborative_broadcasts


async def aget_solo_broadcast(
    id: IDCoercible, rath: LovekitRath | None = None
) -> SoloBroadcast:
    """GetSoloBroadcast

    Get a solo broadcast by ID

    Args:
        id (ID): No description
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        SoloBroadcast
    """
    variables: dict[str, Any] = {}
    variables["id"] = id
    return (await aexecute(GetSoloBroadcastQuery, variables, rath=rath)).solo_broadcast


def get_solo_broadcast(
    id: IDCoercible, rath: LovekitRath | None = None
) -> SoloBroadcast:
    """GetSoloBroadcast

    Get a solo broadcast by ID

    Args:
        id (ID): No description
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        SoloBroadcast
    """
    variables: dict[str, Any] = {}
    variables["id"] = id
    return execute(GetSoloBroadcastQuery, variables, rath=rath).solo_broadcast


async def asearch_solo_broadcast(
    search: str | None | UnsetType = UNSET,
    values: list[IDCoercible] | None | UnsetType = UNSET,
    rath: LovekitRath | None = None,
) -> tuple[SearchSoloBroadcastQueryOptions, ...]:
    """SearchSoloBroadcast

    Get all solo broadcasts

    Args:
        search (str | None, optional): No description.
        values (list[ID] | None, optional): No description.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        list[SearchSoloBroadcastQuerySoloBroadcasts]
    """
    variables: dict[str, Any] = {}
    if search is not UNSET:
        variables["search"] = search
    if values is not UNSET:
        variables["values"] = values
    return (await aexecute(SearchSoloBroadcastQuery, variables, rath=rath)).options


def search_solo_broadcast(
    search: str | None | UnsetType = UNSET,
    values: list[IDCoercible] | None | UnsetType = UNSET,
    rath: LovekitRath | None = None,
) -> tuple[SearchSoloBroadcastQueryOptions, ...]:
    """SearchSoloBroadcast

    Get all solo broadcasts

    Args:
        search (str | None, optional): No description.
        values (list[ID] | None, optional): No description.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        list[SearchSoloBroadcastQuerySoloBroadcasts]
    """
    variables: dict[str, Any] = {}
    if search is not UNSET:
        variables["search"] = search
    if values is not UNSET:
        variables["values"] = values
    return execute(SearchSoloBroadcastQuery, variables, rath=rath).options


async def alist_solo_broadcasts(
    filter: SoloBroadcastFilter | None | UnsetType = UNSET,
    pagination: OffsetPaginationInput | None | UnsetType = UNSET,
    rath: LovekitRath | None = None,
) -> tuple[SoloBroadcast, ...]:
    """ListSoloBroadcasts

    Get all solo broadcasts

    Args:
        filter (SoloBroadcastFilter | None, optional): No description.
        pagination (OffsetPaginationInput | None, optional): No description.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        list[SoloBroadcast]
    """
    variables: dict[str, Any] = {}
    if filter is not UNSET:
        variables["filter"] = filter
    if pagination is not UNSET:
        variables["pagination"] = pagination
    return (
        await aexecute(ListSoloBroadcastsQuery, variables, rath=rath)
    ).solo_broadcasts


def list_solo_broadcasts(
    filter: SoloBroadcastFilter | None | UnsetType = UNSET,
    pagination: OffsetPaginationInput | None | UnsetType = UNSET,
    rath: LovekitRath | None = None,
) -> tuple[SoloBroadcast, ...]:
    """ListSoloBroadcasts

    Get all solo broadcasts

    Args:
        filter (SoloBroadcastFilter | None, optional): No description.
        pagination (OffsetPaginationInput | None, optional): No description.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        list[SoloBroadcast]
    """
    variables: dict[str, Any] = {}
    if filter is not UNSET:
        variables["filter"] = filter
    if pagination is not UNSET:
        variables["pagination"] = pagination
    return execute(ListSoloBroadcastsQuery, variables, rath=rath).solo_broadcasts


async def aget_stream(id: IDCoercible, rath: LovekitRath | None = None) -> Stream:
    """GetStream

    Get a stream by ID

    Args:
        id (ID): No description
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        Stream
    """
    variables: dict[str, Any] = {}
    variables["id"] = id
    return (await aexecute(GetStreamQuery, variables, rath=rath)).stream


def get_stream(id: IDCoercible, rath: LovekitRath | None = None) -> Stream:
    """GetStream

    Get a stream by ID

    Args:
        id (ID): No description
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        Stream
    """
    variables: dict[str, Any] = {}
    variables["id"] = id
    return execute(GetStreamQuery, variables, rath=rath).stream


async def asearch_streams(
    search: str | None | UnsetType = UNSET,
    values: list[IDCoercible] | None | UnsetType = UNSET,
    rath: LovekitRath | None = None,
) -> tuple[SearchStreamsQueryOptions, ...]:
    """SearchStreams

    Get a stream

    Args:
        search (str | None, optional): No description.
        values (list[ID] | None, optional): No description.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        list[SearchStreamsQueryStreams]
    """
    variables: dict[str, Any] = {}
    if search is not UNSET:
        variables["search"] = search
    if values is not UNSET:
        variables["values"] = values
    return (await aexecute(SearchStreamsQuery, variables, rath=rath)).options


def search_streams(
    search: str | None | UnsetType = UNSET,
    values: list[IDCoercible] | None | UnsetType = UNSET,
    rath: LovekitRath | None = None,
) -> tuple[SearchStreamsQueryOptions, ...]:
    """SearchStreams

    Get a stream

    Args:
        search (str | None, optional): No description.
        values (list[ID] | None, optional): No description.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        list[SearchStreamsQueryStreams]
    """
    variables: dict[str, Any] = {}
    if search is not UNSET:
        variables["search"] = search
    if values is not UNSET:
        variables["values"] = values
    return execute(SearchStreamsQuery, variables, rath=rath).options


async def alist_streams(
    filter: StreamFilter | None | UnsetType = UNSET,
    pagination: OffsetPaginationInput | None | UnsetType = UNSET,
    rath: LovekitRath | None = None,
) -> tuple[Stream, ...]:
    """ListStreams

    Get a stream

    Args:
        filter (StreamFilter | None, optional): No description.
        pagination (OffsetPaginationInput | None, optional): No description.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        list[Stream]
    """
    variables: dict[str, Any] = {}
    if filter is not UNSET:
        variables["filter"] = filter
    if pagination is not UNSET:
        variables["pagination"] = pagination
    return (await aexecute(ListStreamsQuery, variables, rath=rath)).streams


def list_streams(
    filter: StreamFilter | None | UnsetType = UNSET,
    pagination: OffsetPaginationInput | None | UnsetType = UNSET,
    rath: LovekitRath | None = None,
) -> tuple[Stream, ...]:
    """ListStreams

    Get a stream

    Args:
        filter (StreamFilter | None, optional): No description.
        pagination (OffsetPaginationInput | None, optional): No description.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        list[Stream]
    """
    variables: dict[str, Any] = {}
    if filter is not UNSET:
        variables["filter"] = filter
    if pagination is not UNSET:
        variables["pagination"] = pagination
    return execute(ListStreamsQuery, variables, rath=rath).streams


CollaborativeBroadcastFilter.model_rebuild()
SoloBroadcastFilter.model_rebuild()
StreamFilter.model_rebuild()
