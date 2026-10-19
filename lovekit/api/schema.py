import builtins
from enum import Enum
from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from rath.scalars import ID, IDCoercible
from typing import Annotated, Iterable, Literal


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
    """What a stream carries"""

    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    __str__ = str.__str__


class DeclareStreamsInput(BaseModel):
    """Every stream an agent offers"""

    streams: tuple["StreamDeclarationInput", ...]
    model_config = ConfigDict(frozen=True, extra="forbid")


class OffsetPaginationInput(BaseModel):
    """No documentation"""

    offset: Annotated[int | None, GraphQLDefault("0")] = None
    "Default: 0"
    limit: int | None = None
    model_config = ConfigDict(frozen=True, extra="forbid")


class StreamDeclarationInput(BaseModel):
    """One stream an agent offers"""

    key: str = Field(
        description="The agent's own name for the stream, the same on every start; its LiveKit track is published under this name"
    )
    title: str | None = Field(
        default=None, description="What the stream is called; the key when not given"
    )
    kind: Annotated[StreamKind | None, GraphQLDefault("VIDEO")] = Field(
        default=None, description="Whether it is video or audio"
    )
    "Whether it is video or audio\nDefault: VIDEO"
    description: str | None = Field(default=None, description="What the stream shows")
    model_config = ConfigDict(frozen=True, extra="forbid")


class StreamFilter(BaseModel):
    """Filter for streams"""

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
    ids: tuple[ID, ...] | None = None
    search: str | None = None
    agent: ID | None = Field(default=None, description="Streams of this agent.")
    client_id: str | None = Field(
        validation_alias=AliasChoices("client_id", "clientId"),
        serialization_alias="clientId",
        default=None,
        description="Streams of the agent running as this client (its OAuth client id), as rekuest knows it too.",
    )
    user_sub: str | None = Field(
        validation_alias=AliasChoices("user_sub", "userSub"),
        serialization_alias="userSub",
        default=None,
        description="Streams of agents running for this user (the `sub` their token carries).",
    )
    live: bool | None = Field(
        default=None,
        description="Only streams their agent publishes right now (true), or does not (false).",
    )
    model_config = ConfigDict(frozen=True, extra="forbid")


class WatchAgentInput(BaseModel):
    """The agent whose streams to watch"""

    agent: ID
    model_config = ConfigDict(frozen=True, extra="forbid")


class WatchStreamInput(BaseModel):
    """The stream to watch"""

    stream: ID
    model_config = ConfigDict(frozen=True, extra="forbid")


class StreamAgent(BaseModel):
    """An app instance that owns live streams: one per client, user and organization"""

    typename: Literal["Agent"] = Field(
        alias="__typename", default="Agent", exclude=True
    )
    id: ID
    room_name: str = Field(alias="roomName")
    "The LiveKit room the agent's streams are tracks in."
    model_config = ConfigDict(frozen=True)


class Stream(BaseModel):
    """One live source an agent offers: a camera, a detector, a microphone"""

    typename: Literal["Stream"] = Field(
        alias="__typename", default="Stream", exclude=True
    )
    id: ID
    key: str
    "The agent's name for the stream, the same across its restarts: the name of the LiveKit track it is published as"
    title: str
    kind: StreamKind
    description: str | None = Field(default=None)
    agent: StreamAgent
    model_config = ConfigDict(frozen=True)

    class Meta:
        """Meta class for Stream"""

        document = "fragment Stream on Stream {\n  id\n  key\n  title\n  kind\n  description\n  agent {\n    id\n    roomName\n    __typename\n  }\n  __typename\n}"
        name = "Stream"
        type = "Stream"


class AgentClient(BaseModel):
    """No documentation"""

    typename: Literal["Client"] = Field(
        alias="__typename", default="Client", exclude=True
    )
    client_id: str = Field(alias="clientId")
    model_config = ConfigDict(frozen=True)


class AgentUser(BaseModel):
    """No documentation"""

    typename: Literal["User"] = Field(alias="__typename", default="User", exclude=True)
    sub: str
    model_config = ConfigDict(frozen=True)


class Agent(BaseModel):
    """An app instance that owns live streams: one per client, user and organization"""

    typename: Literal["Agent"] = Field(
        alias="__typename", default="Agent", exclude=True
    )
    id: ID
    name: str
    "What the agent is called: its client's name, or its client id."
    room_name: str = Field(alias="roomName")
    "The LiveKit room the agent's streams are tracks in."
    client: AgentClient
    user: AgentUser
    streams: tuple[Stream, ...]
    "Every stream the agent offers, as it declared them last"
    model_config = ConfigDict(frozen=True)

    class Meta:
        """Meta class for Agent"""

        document = "fragment Stream on Stream {\n  id\n  key\n  title\n  kind\n  description\n  agent {\n    id\n    roomName\n    __typename\n  }\n  __typename\n}\n\nfragment Agent on Agent {\n  id\n  name\n  roomName\n  client {\n    clientId\n    __typename\n  }\n  user {\n    sub\n    __typename\n  }\n  streams {\n    ...Stream\n    __typename\n  }\n  __typename\n}"
        name = "Agent"
        type = "Agent"


class DeclareStreamsMutation(BaseModel):
    """No documentation found for this operation."""

    declare_streams: tuple[Stream, ...] = Field(alias="declareStreams")
    "Offer exactly these streams as the caller's agent: undeclared ones are removed, unchanged ones untouched"

    class Arguments(BaseModel):
        """Arguments for DeclareStreams"""

        input: DeclareStreamsInput

    class Meta:
        """Meta class for DeclareStreams"""

        document = "fragment Stream on Stream {\n  id\n  key\n  title\n  kind\n  description\n  agent {\n    id\n    roomName\n    __typename\n  }\n  __typename\n}\n\nmutation DeclareStreams($input: DeclareStreamsInput!) {\n  declareStreams(input: $input) {\n    ...Stream\n    __typename\n  }\n}"


class PublishTokenMutation(BaseModel):
    """No documentation found for this operation."""

    publish_token: str = Field(alias="publishToken")
    "A token for the caller's agent to publish its streams; a newer connection replaces an older one"

    class Arguments(BaseModel):
        """Arguments for PublishToken"""

        pass

    class Meta:
        """Meta class for PublishToken"""

        document = "mutation PublishToken {\n  publishToken\n}"


class WatchStreamMutation(BaseModel):
    """No documentation found for this operation."""

    watch_stream: str = Field(alias="watchStream")
    "A token to watch a stream: its agent's room, where it is the track named by its key"

    class Arguments(BaseModel):
        """Arguments for WatchStream"""

        input: WatchStreamInput

    class Meta:
        """Meta class for WatchStream"""

        document = "mutation WatchStream($input: WatchStreamInput!) {\n  watchStream(input: $input)\n}"


class WatchAgentMutation(BaseModel):
    """No documentation found for this operation."""

    watch_agent: str = Field(alias="watchAgent")
    "A token to watch every stream of an agent"

    class Arguments(BaseModel):
        """Arguments for WatchAgent"""

        input: WatchAgentInput

    class Meta:
        """Meta class for WatchAgent"""

        document = "mutation WatchAgent($input: WatchAgentInput!) {\n  watchAgent(input: $input)\n}"


class GetAgentQuery(BaseModel):
    """No documentation found for this operation."""

    agent: Agent
    "Get an agent by ID"

    class Arguments(BaseModel):
        """Arguments for GetAgent"""

        id: ID

    class Meta:
        """Meta class for GetAgent"""

        document = "fragment Stream on Stream {\n  id\n  key\n  title\n  kind\n  description\n  agent {\n    id\n    roomName\n    __typename\n  }\n  __typename\n}\n\nfragment Agent on Agent {\n  id\n  name\n  roomName\n  client {\n    clientId\n    __typename\n  }\n  user {\n    sub\n    __typename\n  }\n  streams {\n    ...Stream\n    __typename\n  }\n  __typename\n}\n\nquery GetAgent($id: ID!) {\n  agent(id: $id) {\n    ...Agent\n    __typename\n  }\n}"


class SearchAgentsQueryOptions(BaseModel):
    """An app instance that owns live streams: one per client, user and organization"""

    typename: Literal["Agent"] = Field(
        alias="__typename", default="Agent", exclude=True
    )
    value: ID
    label: str
    "What the agent is called: its client's name, or its client id."
    model_config = ConfigDict(frozen=True)


class SearchAgentsQuery(BaseModel):
    """No documentation found for this operation."""

    options: tuple[SearchAgentsQueryOptions, ...]
    "The organization's agents that offer streams"

    class Arguments(BaseModel):
        """Arguments for SearchAgents"""

        search: str | None = Field(default=None)
        values: list[ID] | None = Field(default=None)

    class Meta:
        """Meta class for SearchAgents"""

        document = "query SearchAgents($search: String, $values: [ID!]) {\n  options: agents(\n    filters: {search: $search, ids: $values}\n    pagination: {limit: 10}\n  ) {\n    value: id\n    label: name\n    __typename\n  }\n}"


class GetStreamQuery(BaseModel):
    """No documentation found for this operation."""

    stream: Stream
    "Get a stream by ID"

    class Arguments(BaseModel):
        """Arguments for GetStream"""

        id: ID

    class Meta:
        """Meta class for GetStream"""

        document = "fragment Stream on Stream {\n  id\n  key\n  title\n  kind\n  description\n  agent {\n    id\n    roomName\n    __typename\n  }\n  __typename\n}\n\nquery GetStream($id: ID!) {\n  stream(id: $id) {\n    ...Stream\n    __typename\n  }\n}"


class IsStreamLiveQueryStream(BaseModel):
    """One live source an agent offers: a camera, a detector, a microphone"""

    typename: Literal["Stream"] = Field(
        alias="__typename", default="Stream", exclude=True
    )
    live: bool
    "Whether the agent publishes this stream right now: LiveKit's answer, asked when read."
    model_config = ConfigDict(frozen=True)


class IsStreamLiveQuery(BaseModel):
    """No documentation found for this operation."""

    stream: IsStreamLiveQueryStream
    "Get a stream by ID"

    class Arguments(BaseModel):
        """Arguments for IsStreamLive"""

        id: ID

    class Meta:
        """Meta class for IsStreamLive"""

        document = "query IsStreamLive($id: ID!) {\n  stream(id: $id) {\n    live\n    __typename\n  }\n}"


class SearchStreamsQueryOptions(BaseModel):
    """One live source an agent offers: a camera, a detector, a microphone"""

    typename: Literal["Stream"] = Field(
        alias="__typename", default="Stream", exclude=True
    )
    value: ID
    label: str
    model_config = ConfigDict(frozen=True)


class SearchStreamsQuery(BaseModel):
    """No documentation found for this operation."""

    options: tuple[SearchStreamsQueryOptions, ...]
    "The streams of the organization's agents; filter `live` for the ones being published"

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
    "The streams of the organization's agents; filter `live` for the ones being published"

    class Arguments(BaseModel):
        """Arguments for ListStreams"""

        filter: StreamFilter | None = Field(default=None)
        pagination: OffsetPaginationInput | None = Field(default=None)

    class Meta:
        """Meta class for ListStreams"""

        document = "fragment Stream on Stream {\n  id\n  key\n  title\n  kind\n  description\n  agent {\n    id\n    roomName\n    __typename\n  }\n  __typename\n}\n\nquery ListStreams($filter: StreamFilter, $pagination: OffsetPaginationInput) {\n  streams(filters: $filter, pagination: $pagination) {\n    ...Stream\n    __typename\n  }\n}"


class LovekitApi:
    """Every operation of this API as a method. Generated by turms.

    Each method hands its operation to ``execute``, ``aexecute``, ``subscribe``, ``asubscribe`` of ``self``, which the class this one is mixed into (or a base of it) provides.
    """

    async def adeclare_streams(
        self, streams: Iterable[StreamDeclarationInput]
    ) -> tuple[Stream, ...]:
        """DeclareStreams

        Offer exactly these streams as the caller's agent: undeclared ones are removed, unchanged ones untouched

        Args:
            streams: One stream an agent offers (required) (list) (required)

        Returns:
            list[Stream]
        """
        variables: dict[str, builtins.object] = {}
        _input: dict[str, builtins.object] = {}
        _input["streams"] = streams
        variables["input"] = _input
        return (await self.aexecute(DeclareStreamsMutation, variables)).declare_streams

    def declare_streams(
        self, streams: Iterable[StreamDeclarationInput]
    ) -> tuple[Stream, ...]:
        """DeclareStreams

        Offer exactly these streams as the caller's agent: undeclared ones are removed, unchanged ones untouched

        Args:
            streams: One stream an agent offers (required) (list) (required)

        Returns:
            list[Stream]
        """
        variables: dict[str, builtins.object] = {}
        _input: dict[str, builtins.object] = {}
        _input["streams"] = streams
        variables["input"] = _input
        return self.execute(DeclareStreamsMutation, variables).declare_streams

    async def apublish_token(self) -> str:
        """PublishToken

        A token for the caller's agent to publish its streams; a newer connection replaces an older one

        Args:

        Returns:
            str
        """
        variables: dict[str, builtins.object] = {}
        return (await self.aexecute(PublishTokenMutation, variables)).publish_token

    def publish_token(self) -> str:
        """PublishToken

        A token for the caller's agent to publish its streams; a newer connection replaces an older one

        Args:

        Returns:
            str
        """
        variables: dict[str, builtins.object] = {}
        return self.execute(PublishTokenMutation, variables).publish_token

    async def awatch_stream(self, stream: IDCoercible) -> str:
        """WatchStream

        A token to watch a stream: its agent's room, where it is the track named by its key

        Args:
            stream: The `ID` scalar type represents a unique identifier, often used to refetch an object or as key for a cache. The ID type appears in a JSON response as a String; however, it is not intended to be human-readable. When expected as an input type, any string (such as `"4"`) or integer (such as `4`) input value will be accepted as an ID. (required)

        Returns:
            str
        """
        variables: dict[str, builtins.object] = {}
        _input: dict[str, builtins.object] = {}
        _input["stream"] = stream
        variables["input"] = _input
        return (await self.aexecute(WatchStreamMutation, variables)).watch_stream

    def watch_stream(self, stream: IDCoercible) -> str:
        """WatchStream

        A token to watch a stream: its agent's room, where it is the track named by its key

        Args:
            stream: The `ID` scalar type represents a unique identifier, often used to refetch an object or as key for a cache. The ID type appears in a JSON response as a String; however, it is not intended to be human-readable. When expected as an input type, any string (such as `"4"`) or integer (such as `4`) input value will be accepted as an ID. (required)

        Returns:
            str
        """
        variables: dict[str, builtins.object] = {}
        _input: dict[str, builtins.object] = {}
        _input["stream"] = stream
        variables["input"] = _input
        return self.execute(WatchStreamMutation, variables).watch_stream

    async def awatch_agent(self, agent: IDCoercible) -> str:
        """WatchAgent

        A token to watch every stream of an agent

        Args:
            agent: The `ID` scalar type represents a unique identifier, often used to refetch an object or as key for a cache. The ID type appears in a JSON response as a String; however, it is not intended to be human-readable. When expected as an input type, any string (such as `"4"`) or integer (such as `4`) input value will be accepted as an ID. (required)

        Returns:
            str
        """
        variables: dict[str, builtins.object] = {}
        _input: dict[str, builtins.object] = {}
        _input["agent"] = agent
        variables["input"] = _input
        return (await self.aexecute(WatchAgentMutation, variables)).watch_agent

    def watch_agent(self, agent: IDCoercible) -> str:
        """WatchAgent

        A token to watch every stream of an agent

        Args:
            agent: The `ID` scalar type represents a unique identifier, often used to refetch an object or as key for a cache. The ID type appears in a JSON response as a String; however, it is not intended to be human-readable. When expected as an input type, any string (such as `"4"`) or integer (such as `4`) input value will be accepted as an ID. (required)

        Returns:
            str
        """
        variables: dict[str, builtins.object] = {}
        _input: dict[str, builtins.object] = {}
        _input["agent"] = agent
        variables["input"] = _input
        return self.execute(WatchAgentMutation, variables).watch_agent

    async def aget_agent(self, id: IDCoercible) -> Agent:
        """GetAgent

        Get an agent by ID

        Args:
            id (ID): No description

        Returns:
            Agent
        """
        variables: dict[str, builtins.object] = {}
        variables["id"] = id
        return (await self.aexecute(GetAgentQuery, variables)).agent

    def get_agent(self, id: IDCoercible) -> Agent:
        """GetAgent

        Get an agent by ID

        Args:
            id (ID): No description

        Returns:
            Agent
        """
        variables: dict[str, builtins.object] = {}
        variables["id"] = id
        return self.execute(GetAgentQuery, variables).agent

    async def asearch_agents(
        self,
        search: str | None | UnsetType = UNSET,
        values: list[IDCoercible] | None | UnsetType = UNSET,
    ) -> tuple[SearchAgentsQueryOptions, ...]:
        """SearchAgents

        The organization's agents that offer streams

        Args:
            search (str | None, optional): No description.
            values (list[ID] | None, optional): No description.

        Returns:
            list[SearchAgentsQueryAgents]
        """
        variables: dict[str, builtins.object] = {}
        if search is not UNSET:
            variables["search"] = search
        if values is not UNSET:
            variables["values"] = values
        return (await self.aexecute(SearchAgentsQuery, variables)).options

    def search_agents(
        self,
        search: str | None | UnsetType = UNSET,
        values: list[IDCoercible] | None | UnsetType = UNSET,
    ) -> tuple[SearchAgentsQueryOptions, ...]:
        """SearchAgents

        The organization's agents that offer streams

        Args:
            search (str | None, optional): No description.
            values (list[ID] | None, optional): No description.

        Returns:
            list[SearchAgentsQueryAgents]
        """
        variables: dict[str, builtins.object] = {}
        if search is not UNSET:
            variables["search"] = search
        if values is not UNSET:
            variables["values"] = values
        return self.execute(SearchAgentsQuery, variables).options

    async def aget_stream(self, id: IDCoercible) -> Stream:
        """GetStream

        Get a stream by ID

        Args:
            id (ID): No description

        Returns:
            Stream
        """
        variables: dict[str, builtins.object] = {}
        variables["id"] = id
        return (await self.aexecute(GetStreamQuery, variables)).stream

    def get_stream(self, id: IDCoercible) -> Stream:
        """GetStream

        Get a stream by ID

        Args:
            id (ID): No description

        Returns:
            Stream
        """
        variables: dict[str, builtins.object] = {}
        variables["id"] = id
        return self.execute(GetStreamQuery, variables).stream

    async def ais_stream_live(self, id: IDCoercible) -> IsStreamLiveQueryStream:
        """IsStreamLive

        Get a stream by ID

        Args:
            id (ID): No description

        Returns:
            IsStreamLiveQueryStream
        """
        variables: dict[str, builtins.object] = {}
        variables["id"] = id
        return (await self.aexecute(IsStreamLiveQuery, variables)).stream

    def is_stream_live(self, id: IDCoercible) -> IsStreamLiveQueryStream:
        """IsStreamLive

        Get a stream by ID

        Args:
            id (ID): No description

        Returns:
            IsStreamLiveQueryStream
        """
        variables: dict[str, builtins.object] = {}
        variables["id"] = id
        return self.execute(IsStreamLiveQuery, variables).stream

    async def asearch_streams(
        self,
        search: str | None | UnsetType = UNSET,
        values: list[IDCoercible] | None | UnsetType = UNSET,
    ) -> tuple[SearchStreamsQueryOptions, ...]:
        """SearchStreams

        The streams of the organization's agents; filter `live` for the ones being published

        Args:
            search (str | None, optional): No description.
            values (list[ID] | None, optional): No description.

        Returns:
            list[SearchStreamsQueryStreams]
        """
        variables: dict[str, builtins.object] = {}
        if search is not UNSET:
            variables["search"] = search
        if values is not UNSET:
            variables["values"] = values
        return (await self.aexecute(SearchStreamsQuery, variables)).options

    def search_streams(
        self,
        search: str | None | UnsetType = UNSET,
        values: list[IDCoercible] | None | UnsetType = UNSET,
    ) -> tuple[SearchStreamsQueryOptions, ...]:
        """SearchStreams

        The streams of the organization's agents; filter `live` for the ones being published

        Args:
            search (str | None, optional): No description.
            values (list[ID] | None, optional): No description.

        Returns:
            list[SearchStreamsQueryStreams]
        """
        variables: dict[str, builtins.object] = {}
        if search is not UNSET:
            variables["search"] = search
        if values is not UNSET:
            variables["values"] = values
        return self.execute(SearchStreamsQuery, variables).options

    async def alist_streams(
        self,
        filter: StreamFilter | None | UnsetType = UNSET,
        pagination: OffsetPaginationInput | None | UnsetType = UNSET,
    ) -> tuple[Stream, ...]:
        """ListStreams

        The streams of the organization's agents; filter `live` for the ones being published

        Args:
            filter (StreamFilter | None, optional): No description.
            pagination (OffsetPaginationInput | None, optional): No description.

        Returns:
            list[Stream]
        """
        variables: dict[str, builtins.object] = {}
        if filter is not UNSET:
            variables["filter"] = filter
        if pagination is not UNSET:
            variables["pagination"] = pagination
        return (await self.aexecute(ListStreamsQuery, variables)).streams

    def list_streams(
        self,
        filter: StreamFilter | None | UnsetType = UNSET,
        pagination: OffsetPaginationInput | None | UnsetType = UNSET,
    ) -> tuple[Stream, ...]:
        """ListStreams

        The streams of the organization's agents; filter `live` for the ones being published

        Args:
            filter (StreamFilter | None, optional): No description.
            pagination (OffsetPaginationInput | None, optional): No description.

        Returns:
            list[Stream]
        """
        variables: dict[str, builtins.object] = {}
        if filter is not UNSET:
            variables["filter"] = filter
        if pagination is not UNSET:
            variables["pagination"] = pagination
        return self.execute(ListStreamsQuery, variables).streams


DeclareStreamsInput.model_rebuild()
StreamFilter.model_rebuild()
