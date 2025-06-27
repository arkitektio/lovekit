from typing import Literal, Tuple, Optional, List
from pydantic import ConfigDict, Field, BaseModel
from enum import Enum
from lovekit.funcs import execute, aexecute
from rath.scalars import ID
from lovekit.rath import LovekitRath


class StreamKind(str, Enum):
    """The state of a dask cluster"""

    VIDEO = "VIDEO"
    AUDIO = "AUDIO"


class OffsetPaginationInput(BaseModel):
    offset: int
    limit: Optional[int] = None
    model_config = ConfigDict(
        frozen=True, extra="forbid", populate_by_name=True, use_enum_values=True
    )


class CollaborativeBroadcastFilter(BaseModel):
    """Filter for Solo Broadcasts"""

    ids: Optional[Tuple[ID, ...]] = None
    search: Optional[str] = None
    and_: Optional["CollaborativeBroadcastFilter"] = Field(alias="AND", default=None)
    or_: Optional["CollaborativeBroadcastFilter"] = Field(alias="OR", default=None)
    not_: Optional["CollaborativeBroadcastFilter"] = Field(alias="NOT", default=None)
    distinct: Optional[bool] = Field(alias="DISTINCT", default=None)
    model_config = ConfigDict(
        frozen=True, extra="forbid", populate_by_name=True, use_enum_values=True
    )


class StreamFilter(BaseModel):
    """Filter for Streams"""

    ids: Optional[Tuple[ID, ...]] = None
    search: Optional[str] = None
    and_: Optional["StreamFilter"] = Field(alias="AND", default=None)
    or_: Optional["StreamFilter"] = Field(alias="OR", default=None)
    not_: Optional["StreamFilter"] = Field(alias="NOT", default=None)
    distinct: Optional[bool] = Field(alias="DISTINCT", default=None)
    model_config = ConfigDict(
        frozen=True, extra="forbid", populate_by_name=True, use_enum_values=True
    )


class SoloBroadcastFilter(BaseModel):
    """Filter for Solo Broadcasts"""

    ids: Optional[Tuple[ID, ...]] = None
    search: Optional[str] = None
    and_: Optional["SoloBroadcastFilter"] = Field(alias="AND", default=None)
    or_: Optional["SoloBroadcastFilter"] = Field(alias="OR", default=None)
    not_: Optional["SoloBroadcastFilter"] = Field(alias="NOT", default=None)
    distinct: Optional[bool] = Field(alias="DISTINCT", default=None)
    model_config = ConfigDict(
        frozen=True, extra="forbid", populate_by_name=True, use_enum_values=True
    )


class EnsureSoloBroadcastInput(BaseModel):
    instance_id: Optional[str] = Field(alias="instanceId", default=None)
    title: Optional[str] = None
    model_config = ConfigDict(
        frozen=True, extra="forbid", populate_by_name=True, use_enum_values=True
    )


class EnsureStreamInput(BaseModel):
    broadcast: Optional[ID] = None
    kind: StreamKind
    title: Optional[str] = None
    model_config = ConfigDict(
        frozen=True, extra="forbid", populate_by_name=True, use_enum_values=True
    )


class Stream(BaseModel):
    typename: Literal["Stream"] = Field(
        alias="__typename", default="Stream", exclude=True
    )
    id: ID
    model_config = ConfigDict(frozen=True)


class StreamerUser(BaseModel):
    typename: Literal["User"] = Field(alias="__typename", default="User", exclude=True)
    sub: str
    model_config = ConfigDict(frozen=True)


class StreamerClient(BaseModel):
    typename: Literal["Client"] = Field(
        alias="__typename", default="Client", exclude=True
    )
    client_id: str = Field(alias="clientId")
    model_config = ConfigDict(frozen=True)


class Streamer(BaseModel):
    typename: Literal["Streamer"] = Field(
        alias="__typename", default="Streamer", exclude=True
    )
    user: StreamerUser
    client: StreamerClient
    model_config = ConfigDict(frozen=True)


class SoloBroadcast(BaseModel):
    typename: Literal["SoloBroadcast"] = Field(
        alias="__typename", default="SoloBroadcast", exclude=True
    )
    id: ID
    title: str
    streamer: Streamer
    model_config = ConfigDict(frozen=True)


class CollaborativeBroadcast(BaseModel):
    typename: Literal["CollaborativeBroadcast"] = Field(
        alias="__typename", default="CollaborativeBroadcast", exclude=True
    )
    id: ID
    title: str
    streamers: Tuple[Streamer, ...]
    "The streamers that are collaborating on this broadcast."
    model_config = ConfigDict(frozen=True)


class EnsureStreamMutation(BaseModel):
    ensure_stream: str = Field(alias="ensureStream")
    "Create a stream and return the token for it"

    class Arguments(BaseModel):
        input: EnsureStreamInput

    class Meta:
        document = "mutation EnsureStream($input: EnsureStreamInput!) {\n  ensureStream(input: $input)\n}"


class EnsureSoloBroadcastMutation(BaseModel):
    ensure_solo_broadcast: SoloBroadcast = Field(alias="ensureSoloBroadcast")
    "Create a solo broadcast"

    class Arguments(BaseModel):
        input: EnsureSoloBroadcastInput

    class Meta:
        document = "fragment Streamer on Streamer {\n  user {\n    sub\n    __typename\n  }\n  client {\n    clientId\n    __typename\n  }\n  __typename\n}\n\nfragment SoloBroadcast on SoloBroadcast {\n  id\n  title\n  streamer {\n    ...Streamer\n    __typename\n  }\n  __typename\n}\n\nmutation EnsureSoloBroadcast($input: EnsureSoloBroadcastInput!) {\n  ensureSoloBroadcast(input: $input) {\n    ...SoloBroadcast\n    __typename\n  }\n}"


class GetStreamQuery(BaseModel):
    stream: Stream
    "Get a stream by ID"

    class Arguments(BaseModel):
        id: ID

    class Meta:
        document = "fragment Stream on Stream {\n  id\n  __typename\n}\n\nquery GetStream($id: ID!) {\n  stream(id: $id) {\n    ...Stream\n    __typename\n  }\n}"


class SearchStreamsQueryOptions(BaseModel):
    typename: Literal["Stream"] = Field(
        alias="__typename", default="Stream", exclude=True
    )
    value: ID
    label: str
    model_config = ConfigDict(frozen=True)


class SearchStreamsQuery(BaseModel):
    options: Tuple[SearchStreamsQueryOptions, ...]
    "Get a stream"

    class Arguments(BaseModel):
        search: Optional[str] = Field(default=None)
        values: Optional[List[ID]] = Field(default=None)

    class Meta:
        document = "query SearchStreams($search: String, $values: [ID!]) {\n  options: streams(\n    filters: {search: $search, ids: $values}\n    pagination: {limit: 10}\n  ) {\n    value: id\n    label: title\n    __typename\n  }\n}"


class ListStreamsQuery(BaseModel):
    streams: Tuple[Stream, ...]
    "Get a stream"

    class Arguments(BaseModel):
        filter: Optional[StreamFilter] = Field(default=None)
        pagination: Optional[OffsetPaginationInput] = Field(default=None)

    class Meta:
        document = "fragment Stream on Stream {\n  id\n  __typename\n}\n\nquery ListStreams($filter: StreamFilter, $pagination: OffsetPaginationInput) {\n  streams(filters: $filter, pagination: $pagination) {\n    ...Stream\n    __typename\n  }\n}"


class GetCollaborativeBroadcastQuery(BaseModel):
    collaborative_broadcast: CollaborativeBroadcast = Field(
        alias="collaborativeBroadcast"
    )
    "Get a collaborative broadcast by ID"

    class Arguments(BaseModel):
        id: ID

    class Meta:
        document = "fragment Streamer on Streamer {\n  user {\n    sub\n    __typename\n  }\n  client {\n    clientId\n    __typename\n  }\n  __typename\n}\n\nfragment CollaborativeBroadcast on CollaborativeBroadcast {\n  id\n  title\n  streamers {\n    ...Streamer\n    __typename\n  }\n  __typename\n}\n\nquery GetCollaborativeBroadcast($id: ID!) {\n  collaborativeBroadcast(id: $id) {\n    ...CollaborativeBroadcast\n    __typename\n  }\n}"


class SearchollaborativeBroadcastsQueryOptions(BaseModel):
    typename: Literal["CollaborativeBroadcast"] = Field(
        alias="__typename", default="CollaborativeBroadcast", exclude=True
    )
    value: ID
    label: str
    model_config = ConfigDict(frozen=True)


class SearchollaborativeBroadcastsQuery(BaseModel):
    options: Tuple[SearchollaborativeBroadcastsQueryOptions, ...]
    "Get all collaborative broadcasts"

    class Arguments(BaseModel):
        search: Optional[str] = Field(default=None)
        values: Optional[List[ID]] = Field(default=None)

    class Meta:
        document = "query SearchollaborativeBroadcasts($search: String, $values: [ID!]) {\n  options: collaborativeBroadcasts(\n    filters: {search: $search, ids: $values}\n    pagination: {limit: 10}\n  ) {\n    value: id\n    label: title\n    __typename\n  }\n}"


class ListCollaborativeBroadcastsQuery(BaseModel):
    collaborative_broadcasts: Tuple[CollaborativeBroadcast, ...] = Field(
        alias="collaborativeBroadcasts"
    )
    "Get all collaborative broadcasts"

    class Arguments(BaseModel):
        filter: Optional[CollaborativeBroadcastFilter] = Field(default=None)
        pagination: Optional[OffsetPaginationInput] = Field(default=None)

    class Meta:
        document = "fragment Streamer on Streamer {\n  user {\n    sub\n    __typename\n  }\n  client {\n    clientId\n    __typename\n  }\n  __typename\n}\n\nfragment CollaborativeBroadcast on CollaborativeBroadcast {\n  id\n  title\n  streamers {\n    ...Streamer\n    __typename\n  }\n  __typename\n}\n\nquery ListCollaborativeBroadcasts($filter: CollaborativeBroadcastFilter, $pagination: OffsetPaginationInput) {\n  collaborativeBroadcasts(filters: $filter, pagination: $pagination) {\n    ...CollaborativeBroadcast\n    __typename\n  }\n}"


class GetSoloBroadcastQuery(BaseModel):
    solo_broadcast: SoloBroadcast = Field(alias="soloBroadcast")
    "Get a solo broadcast by ID"

    class Arguments(BaseModel):
        id: ID

    class Meta:
        document = "fragment Streamer on Streamer {\n  user {\n    sub\n    __typename\n  }\n  client {\n    clientId\n    __typename\n  }\n  __typename\n}\n\nfragment SoloBroadcast on SoloBroadcast {\n  id\n  title\n  streamer {\n    ...Streamer\n    __typename\n  }\n  __typename\n}\n\nquery GetSoloBroadcast($id: ID!) {\n  soloBroadcast(id: $id) {\n    ...SoloBroadcast\n    __typename\n  }\n}"


class SearchSoloBroadcastQueryOptions(BaseModel):
    typename: Literal["SoloBroadcast"] = Field(
        alias="__typename", default="SoloBroadcast", exclude=True
    )
    value: ID
    label: str
    model_config = ConfigDict(frozen=True)


class SearchSoloBroadcastQuery(BaseModel):
    options: Tuple[SearchSoloBroadcastQueryOptions, ...]
    "Get all solo broadcasts"

    class Arguments(BaseModel):
        search: Optional[str] = Field(default=None)
        values: Optional[List[ID]] = Field(default=None)

    class Meta:
        document = "query SearchSoloBroadcast($search: String, $values: [ID!]) {\n  options: soloBroadcasts(\n    filters: {search: $search, ids: $values}\n    pagination: {limit: 10}\n  ) {\n    value: id\n    label: title\n    __typename\n  }\n}"


class ListSoloBroadcastsQuery(BaseModel):
    solo_broadcasts: Tuple[SoloBroadcast, ...] = Field(alias="soloBroadcasts")
    "Get all solo broadcasts"

    class Arguments(BaseModel):
        filter: Optional[SoloBroadcastFilter] = Field(default=None)
        pagination: Optional[OffsetPaginationInput] = Field(default=None)

    class Meta:
        document = "fragment Streamer on Streamer {\n  user {\n    sub\n    __typename\n  }\n  client {\n    clientId\n    __typename\n  }\n  __typename\n}\n\nfragment SoloBroadcast on SoloBroadcast {\n  id\n  title\n  streamer {\n    ...Streamer\n    __typename\n  }\n  __typename\n}\n\nquery ListSoloBroadcasts($filter: SoloBroadcastFilter, $pagination: OffsetPaginationInput) {\n  soloBroadcasts(filters: $filter, pagination: $pagination) {\n    ...SoloBroadcast\n    __typename\n  }\n}"


async def aensure_stream(
    kind: StreamKind,
    broadcast: Optional[ID] = None,
    title: Optional[str] = None,
    rath: Optional[LovekitRath] = None,
) -> str:
    """EnsureStream

    Create a stream and return the token for it

    Arguments:
        broadcast: The `ID` scalar type represents a unique identifier, often used to refetch an object or as key for a cache. The ID type appears in a JSON response as a String; however, it is not intended to be human-readable. When expected as an input type, any string (such as `"4"`) or integer (such as `4`) input value will be accepted as an ID.
        kind: StreamKind (required)
        title: The `String` scalar type represents textual data, represented as UTF-8 character sequences. The String type is most often used by GraphQL to represent free-form human-readable text.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        str
    """
    return (
        await aexecute(
            EnsureStreamMutation,
            {"input": {"broadcast": broadcast, "kind": kind, "title": title}},
            rath=rath,
        )
    ).ensure_stream


def ensure_stream(
    kind: StreamKind,
    broadcast: Optional[ID] = None,
    title: Optional[str] = None,
    rath: Optional[LovekitRath] = None,
) -> str:
    """EnsureStream

    Create a stream and return the token for it

    Arguments:
        broadcast: The `ID` scalar type represents a unique identifier, often used to refetch an object or as key for a cache. The ID type appears in a JSON response as a String; however, it is not intended to be human-readable. When expected as an input type, any string (such as `"4"`) or integer (such as `4`) input value will be accepted as an ID.
        kind: StreamKind (required)
        title: The `String` scalar type represents textual data, represented as UTF-8 character sequences. The String type is most often used by GraphQL to represent free-form human-readable text.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        str
    """
    return execute(
        EnsureStreamMutation,
        {"input": {"broadcast": broadcast, "kind": kind, "title": title}},
        rath=rath,
    ).ensure_stream


async def aensure_solo_broadcast(
    instance_id: Optional[str] = None,
    title: Optional[str] = None,
    rath: Optional[LovekitRath] = None,
) -> SoloBroadcast:
    """EnsureSoloBroadcast

    Create a solo broadcast

    Arguments:
        instance_id: The `String` scalar type represents textual data, represented as UTF-8 character sequences. The String type is most often used by GraphQL to represent free-form human-readable text.
        title: The `String` scalar type represents textual data, represented as UTF-8 character sequences. The String type is most often used by GraphQL to represent free-form human-readable text.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        SoloBroadcast
    """
    return (
        await aexecute(
            EnsureSoloBroadcastMutation,
            {"input": {"instanceId": instance_id, "title": title}},
            rath=rath,
        )
    ).ensure_solo_broadcast


def ensure_solo_broadcast(
    instance_id: Optional[str] = None,
    title: Optional[str] = None,
    rath: Optional[LovekitRath] = None,
) -> SoloBroadcast:
    """EnsureSoloBroadcast

    Create a solo broadcast

    Arguments:
        instance_id: The `String` scalar type represents textual data, represented as UTF-8 character sequences. The String type is most often used by GraphQL to represent free-form human-readable text.
        title: The `String` scalar type represents textual data, represented as UTF-8 character sequences. The String type is most often used by GraphQL to represent free-form human-readable text.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        SoloBroadcast
    """
    return execute(
        EnsureSoloBroadcastMutation,
        {"input": {"instanceId": instance_id, "title": title}},
        rath=rath,
    ).ensure_solo_broadcast


async def aget_stream(id: ID, rath: Optional[LovekitRath] = None) -> Stream:
    """GetStream

    Get a stream by ID

    Arguments:
        id (ID): No description
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        Stream
    """
    return (await aexecute(GetStreamQuery, {"id": id}, rath=rath)).stream


def get_stream(id: ID, rath: Optional[LovekitRath] = None) -> Stream:
    """GetStream

    Get a stream by ID

    Arguments:
        id (ID): No description
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        Stream
    """
    return execute(GetStreamQuery, {"id": id}, rath=rath).stream


async def asearch_streams(
    search: Optional[str] = None,
    values: Optional[List[ID]] = None,
    rath: Optional[LovekitRath] = None,
) -> List[SearchStreamsQueryOptions]:
    """SearchStreams

    Get a stream

    Arguments:
        search (Optional[str], optional): No description.
        values (Optional[List[ID]], optional): No description.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        List[SearchStreamsQueryStreams]
    """
    return (
        await aexecute(
            SearchStreamsQuery, {"search": search, "values": values}, rath=rath
        )
    ).options


def search_streams(
    search: Optional[str] = None,
    values: Optional[List[ID]] = None,
    rath: Optional[LovekitRath] = None,
) -> List[SearchStreamsQueryOptions]:
    """SearchStreams

    Get a stream

    Arguments:
        search (Optional[str], optional): No description.
        values (Optional[List[ID]], optional): No description.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        List[SearchStreamsQueryStreams]
    """
    return execute(
        SearchStreamsQuery, {"search": search, "values": values}, rath=rath
    ).options


async def alist_streams(
    filter: Optional[StreamFilter] = None,
    pagination: Optional[OffsetPaginationInput] = None,
    rath: Optional[LovekitRath] = None,
) -> List[Stream]:
    """ListStreams

    Get a stream

    Arguments:
        filter (Optional[StreamFilter], optional): No description.
        pagination (Optional[OffsetPaginationInput], optional): No description.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        List[Stream]
    """
    return (
        await aexecute(
            ListStreamsQuery, {"filter": filter, "pagination": pagination}, rath=rath
        )
    ).streams


def list_streams(
    filter: Optional[StreamFilter] = None,
    pagination: Optional[OffsetPaginationInput] = None,
    rath: Optional[LovekitRath] = None,
) -> List[Stream]:
    """ListStreams

    Get a stream

    Arguments:
        filter (Optional[StreamFilter], optional): No description.
        pagination (Optional[OffsetPaginationInput], optional): No description.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        List[Stream]
    """
    return execute(
        ListStreamsQuery, {"filter": filter, "pagination": pagination}, rath=rath
    ).streams


async def aget_collaborative_broadcast(
    id: ID, rath: Optional[LovekitRath] = None
) -> CollaborativeBroadcast:
    """GetCollaborativeBroadcast

    Get a collaborative broadcast by ID

    Arguments:
        id (ID): No description
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        CollaborativeBroadcast
    """
    return (
        await aexecute(GetCollaborativeBroadcastQuery, {"id": id}, rath=rath)
    ).collaborative_broadcast


def get_collaborative_broadcast(
    id: ID, rath: Optional[LovekitRath] = None
) -> CollaborativeBroadcast:
    """GetCollaborativeBroadcast

    Get a collaborative broadcast by ID

    Arguments:
        id (ID): No description
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        CollaborativeBroadcast
    """
    return execute(
        GetCollaborativeBroadcastQuery, {"id": id}, rath=rath
    ).collaborative_broadcast


async def asearchollaborative_broadcasts(
    search: Optional[str] = None,
    values: Optional[List[ID]] = None,
    rath: Optional[LovekitRath] = None,
) -> List[SearchollaborativeBroadcastsQueryOptions]:
    """SearchollaborativeBroadcasts

    Get all collaborative broadcasts

    Arguments:
        search (Optional[str], optional): No description.
        values (Optional[List[ID]], optional): No description.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        List[SearchollaborativeBroadcastsQueryCollaborativebroadcasts]
    """
    return (
        await aexecute(
            SearchollaborativeBroadcastsQuery,
            {"search": search, "values": values},
            rath=rath,
        )
    ).options


def searchollaborative_broadcasts(
    search: Optional[str] = None,
    values: Optional[List[ID]] = None,
    rath: Optional[LovekitRath] = None,
) -> List[SearchollaborativeBroadcastsQueryOptions]:
    """SearchollaborativeBroadcasts

    Get all collaborative broadcasts

    Arguments:
        search (Optional[str], optional): No description.
        values (Optional[List[ID]], optional): No description.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        List[SearchollaborativeBroadcastsQueryCollaborativebroadcasts]
    """
    return execute(
        SearchollaborativeBroadcastsQuery,
        {"search": search, "values": values},
        rath=rath,
    ).options


async def alist_collaborative_broadcasts(
    filter: Optional[CollaborativeBroadcastFilter] = None,
    pagination: Optional[OffsetPaginationInput] = None,
    rath: Optional[LovekitRath] = None,
) -> List[CollaborativeBroadcast]:
    """ListCollaborativeBroadcasts

    Get all collaborative broadcasts

    Arguments:
        filter (Optional[CollaborativeBroadcastFilter], optional): No description.
        pagination (Optional[OffsetPaginationInput], optional): No description.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        List[CollaborativeBroadcast]
    """
    return (
        await aexecute(
            ListCollaborativeBroadcastsQuery,
            {"filter": filter, "pagination": pagination},
            rath=rath,
        )
    ).collaborative_broadcasts


def list_collaborative_broadcasts(
    filter: Optional[CollaborativeBroadcastFilter] = None,
    pagination: Optional[OffsetPaginationInput] = None,
    rath: Optional[LovekitRath] = None,
) -> List[CollaborativeBroadcast]:
    """ListCollaborativeBroadcasts

    Get all collaborative broadcasts

    Arguments:
        filter (Optional[CollaborativeBroadcastFilter], optional): No description.
        pagination (Optional[OffsetPaginationInput], optional): No description.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        List[CollaborativeBroadcast]
    """
    return execute(
        ListCollaborativeBroadcastsQuery,
        {"filter": filter, "pagination": pagination},
        rath=rath,
    ).collaborative_broadcasts


async def aget_solo_broadcast(
    id: ID, rath: Optional[LovekitRath] = None
) -> SoloBroadcast:
    """GetSoloBroadcast

    Get a solo broadcast by ID

    Arguments:
        id (ID): No description
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        SoloBroadcast
    """
    return (await aexecute(GetSoloBroadcastQuery, {"id": id}, rath=rath)).solo_broadcast


def get_solo_broadcast(id: ID, rath: Optional[LovekitRath] = None) -> SoloBroadcast:
    """GetSoloBroadcast

    Get a solo broadcast by ID

    Arguments:
        id (ID): No description
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        SoloBroadcast
    """
    return execute(GetSoloBroadcastQuery, {"id": id}, rath=rath).solo_broadcast


async def asearch_solo_broadcast(
    search: Optional[str] = None,
    values: Optional[List[ID]] = None,
    rath: Optional[LovekitRath] = None,
) -> List[SearchSoloBroadcastQueryOptions]:
    """SearchSoloBroadcast

    Get all solo broadcasts

    Arguments:
        search (Optional[str], optional): No description.
        values (Optional[List[ID]], optional): No description.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        List[SearchSoloBroadcastQuerySolobroadcasts]
    """
    return (
        await aexecute(
            SearchSoloBroadcastQuery, {"search": search, "values": values}, rath=rath
        )
    ).options


def search_solo_broadcast(
    search: Optional[str] = None,
    values: Optional[List[ID]] = None,
    rath: Optional[LovekitRath] = None,
) -> List[SearchSoloBroadcastQueryOptions]:
    """SearchSoloBroadcast

    Get all solo broadcasts

    Arguments:
        search (Optional[str], optional): No description.
        values (Optional[List[ID]], optional): No description.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        List[SearchSoloBroadcastQuerySolobroadcasts]
    """
    return execute(
        SearchSoloBroadcastQuery, {"search": search, "values": values}, rath=rath
    ).options


async def alist_solo_broadcasts(
    filter: Optional[SoloBroadcastFilter] = None,
    pagination: Optional[OffsetPaginationInput] = None,
    rath: Optional[LovekitRath] = None,
) -> List[SoloBroadcast]:
    """ListSoloBroadcasts

    Get all solo broadcasts

    Arguments:
        filter (Optional[SoloBroadcastFilter], optional): No description.
        pagination (Optional[OffsetPaginationInput], optional): No description.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        List[SoloBroadcast]
    """
    return (
        await aexecute(
            ListSoloBroadcastsQuery,
            {"filter": filter, "pagination": pagination},
            rath=rath,
        )
    ).solo_broadcasts


def list_solo_broadcasts(
    filter: Optional[SoloBroadcastFilter] = None,
    pagination: Optional[OffsetPaginationInput] = None,
    rath: Optional[LovekitRath] = None,
) -> List[SoloBroadcast]:
    """ListSoloBroadcasts

    Get all solo broadcasts

    Arguments:
        filter (Optional[SoloBroadcastFilter], optional): No description.
        pagination (Optional[OffsetPaginationInput], optional): No description.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        List[SoloBroadcast]
    """
    return execute(
        ListSoloBroadcastsQuery, {"filter": filter, "pagination": pagination}, rath=rath
    ).solo_broadcasts


CollaborativeBroadcastFilter.model_rebuild()
SoloBroadcastFilter.model_rebuild()
StreamFilter.model_rebuild()
