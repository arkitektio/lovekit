import builtins
from enum import Enum
from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from rath.scalars import ID, IDCoercible
from typing import Annotated, ClassVar, Iterable, Literal


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


class AxisType(str, Enum):
    """The semantic kind of an axis, as mikro's coordinate systems name them"""

    SPACE = "SPACE"
    TIME = "TIME"
    CHANNEL = "CHANNEL"
    COORDINATE = "COORDINATE"
    DISPLACEMENT = "DISPLACEMENT"
    MICROTIME = "MICROTIME"
    SPECTRUM = "SPECTRUM"
    INDEX = "INDEX"
    VALUE = "VALUE"
    CATEGORY = "CATEGORY"
    __str__ = str.__str__


class StreamKind(str, Enum):
    """What a stream carries"""

    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    DATA = "DATA"
    __str__ = str.__str__


class Transport(str, Enum):
    """How a stream is carried from its agent to whoever watches"""

    LIVEKIT = "LIVEKIT"
    __str__ = str.__str__


class AxisInput(BaseModel):
    """One axis of a data stream's frames: its name and its semantic kind. Units belong to a calibration"""

    name: str = Field(description="The name of the axis, e.g. 'wavelength'")
    type: AxisType = Field(description="The semantic kind of the axis")
    model_config = ConfigDict(frozen=True, extra="forbid")


class CalibrationInput(BaseModel):
    """What a step along one axis measures: position = offset + scale * index, in unit"""

    axis: str = Field(description="The name of the axis this calibrates")
    unit: str = Field(description="The unit of the calibrated position, e.g. 'nm'")
    scale: Annotated[float | None, GraphQLDefault("1.0")] = Field(
        default=None, description="The step between two neighbouring values"
    )
    "The step between two neighbouring values\nDefault: 1.0"
    offset: Annotated[float | None, GraphQLDefault("0.0")] = Field(
        default=None, description="The position of the first value"
    )
    "The position of the first value\nDefault: 0.0"
    model_config = ConfigDict(frozen=True, extra="forbid")


class DataFormatInput(BaseModel):
    """What every frame of a data stream holds"""

    dtype: str = Field(
        description="The type of one value, as numpy names it: uint8, int16, float16, float32, ..."
    )
    shape: tuple[int, ...] = Field(
        description="The shape of one frame; a frame is at most 1024 bytes"
    )
    axes: tuple[AxisInput, ...] = Field(
        description="One axis per dimension of the shape, in its order"
    )
    calibration: Annotated[
        tuple[CalibrationInput, ...] | None, GraphQLDefault("[]")
    ] = Field(default=None, description="The axes that measure something, and what")
    "The axes that measure something, and what\nDefault: []"
    unit: str | None = Field(
        default=None, description="The unit of the values themselves, e.g. 'counts'"
    )
    reference: str | None = Field(
        default=None,
        description="The space the axes are in, named as mikro names a coordinate system's reference: stored data of the same reference is in the same space",
    )
    model_config = ConfigDict(frozen=True, extra="forbid")


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
        default=None, description="Whether it is video, audio or data"
    )
    "Whether it is video, audio or data\nDefault: VIDEO"
    description: str | None = Field(default=None, description="What the stream shows")
    format: DataFormatInput | None = Field(
        default=None,
        description="What a frame holds: needed for a data stream, refused for any other",
    )
    model_config = ConfigDict(frozen=True, extra="forbid")


class StreamFilter(BaseModel):
    """Filter for streams"""

    in_collaboration: ID | None = Field(
        validation_alias=AliasChoices("in_collaboration", "inCollaboration"),
        serialization_alias="inCollaboration",
        default=None,
        description="Only what is in this collaboration (its key): put in, or part of what was",
    )
    created_under: ID | None = Field(
        validation_alias=AliasChoices("created_under", "createdUnder"),
        serialization_alias="createdUnder",
        default=None,
        description="Only what the workflow (its root task id) created",
    )
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


class Connection(BaseModel):
    """What it takes to reach an agent's streams or a call: the carrier, and what lets the caller in. Where the carrier is, the client knows from its own configuration"""

    typename: Literal["Connection"] = Field(
        alias="__typename", default="Connection", exclude=True
    )
    transport: Transport
    credential: str
    "What lets the caller in: for LIVEKIT, the access token of its room"
    model_config = ConfigDict(frozen=True)

    class Meta:
        """Meta class for Connection"""

        document = "fragment Connection on Connection {\n  transport\n  credential\n  __typename\n}"
        name = "Connection"
        type = "Connection"


class DataFormatAxes(BaseModel):
    """One axis of a data stream's frames"""

    typename: Literal["Axis"] = Field(alias="__typename", default="Axis", exclude=True)
    name: str
    type: AxisType
    model_config = ConfigDict(frozen=True)


class DataFormatCalibration(BaseModel):
    """What a step along one axis measures: position = offset + scale * index, in unit"""

    typename: Literal["Calibration"] = Field(
        alias="__typename", default="Calibration", exclude=True
    )
    axis: str
    unit: str
    scale: float
    offset: float
    model_config = ConfigDict(frozen=True)


class DataFormat(BaseModel):
    """What every frame of a data stream holds"""

    typename: Literal["DataFormat"] = Field(
        alias="__typename", default="DataFormat", exclude=True
    )
    dtype: str
    "The type of one value, as numpy names it"
    shape: tuple[int, ...]
    unit: str | None = Field(default=None)
    "The unit of the values themselves"
    reference: str | None = Field(default=None)
    "The space the axes are in, named as mikro names a coordinate system's reference"
    axes: tuple[DataFormatAxes, ...]
    "One axis per dimension of the shape, in its order"
    calibration: tuple[DataFormatCalibration, ...]
    model_config = ConfigDict(frozen=True)

    class Meta:
        """Meta class for DataFormat"""

        document = "fragment DataFormat on DataFormat {\n  dtype\n  shape\n  unit\n  reference\n  axes {\n    name\n    type\n    __typename\n  }\n  calibration {\n    axis\n    unit\n    scale\n    offset\n    __typename\n  }\n  __typename\n}"
        name = "DataFormat"
        type = "DataFormat"


class StreamAgent(BaseModel):
    """An app instance that owns live streams: one per client, user and organization"""

    __identifier__: ClassVar[Literal["@lovekit/agent"]] = "@lovekit/agent"
    typename: Literal["Agent"] = Field(
        alias="__typename", default="Agent", exclude=True
    )
    id: ID
    room_name: str = Field(alias="roomName")
    "The LiveKit room the agent's streams are tracks in."
    model_config = ConfigDict(frozen=True)


class Stream(BaseModel):
    """One live source an agent offers: a camera, a detector, a microphone, a spectrometer"""

    __identifier__: ClassVar[Literal["@lovekit/stream"]] = "@lovekit/stream"
    typename: Literal["Stream"] = Field(
        alias="__typename", default="Stream", exclude=True
    )
    id: ID
    key: str
    "The agent's name for the stream, the same across its restarts: the name of the LiveKit track it is published as"
    title: str
    kind: StreamKind
    description: str | None = Field(default=None)
    format: DataFormat | None = Field(default=None)
    "What a frame holds; only a data stream has one."
    agent: StreamAgent
    model_config = ConfigDict(frozen=True)

    class Meta:
        """Meta class for Stream"""

        document = "fragment DataFormat on DataFormat {\n  dtype\n  shape\n  unit\n  reference\n  axes {\n    name\n    type\n    __typename\n  }\n  calibration {\n    axis\n    unit\n    scale\n    offset\n    __typename\n  }\n  __typename\n}\n\nfragment Stream on Stream {\n  id\n  key\n  title\n  kind\n  description\n  format {\n    ...DataFormat\n    __typename\n  }\n  agent {\n    id\n    roomName\n    __typename\n  }\n  __typename\n}"
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

    __identifier__: ClassVar[Literal["@lovekit/agent"]] = "@lovekit/agent"
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

        document = "fragment DataFormat on DataFormat {\n  dtype\n  shape\n  unit\n  reference\n  axes {\n    name\n    type\n    __typename\n  }\n  calibration {\n    axis\n    unit\n    scale\n    offset\n    __typename\n  }\n  __typename\n}\n\nfragment Stream on Stream {\n  id\n  key\n  title\n  kind\n  description\n  format {\n    ...DataFormat\n    __typename\n  }\n  agent {\n    id\n    roomName\n    __typename\n  }\n  __typename\n}\n\nfragment Agent on Agent {\n  id\n  name\n  roomName\n  client {\n    clientId\n    __typename\n  }\n  user {\n    sub\n    __typename\n  }\n  streams {\n    ...Stream\n    __typename\n  }\n  __typename\n}"
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

        document = "fragment DataFormat on DataFormat {\n  dtype\n  shape\n  unit\n  reference\n  axes {\n    name\n    type\n    __typename\n  }\n  calibration {\n    axis\n    unit\n    scale\n    offset\n    __typename\n  }\n  __typename\n}\n\nfragment Stream on Stream {\n  id\n  key\n  title\n  kind\n  description\n  format {\n    ...DataFormat\n    __typename\n  }\n  agent {\n    id\n    roomName\n    __typename\n  }\n  __typename\n}\n\nmutation DeclareStreams($input: DeclareStreamsInput!) {\n  declareStreams(input: $input) {\n    ...Stream\n    __typename\n  }\n}"


class PublisherConnectionMutation(BaseModel):
    """No documentation found for this operation."""

    publisher_connection: Connection = Field(alias="publisherConnection")
    "What the caller's agent publishes its streams with; a newer connection replaces an older one"

    class Arguments(BaseModel):
        """Arguments for PublisherConnection"""

        pass

    class Meta:
        """Meta class for PublisherConnection"""

        document = "fragment Connection on Connection {\n  transport\n  credential\n  __typename\n}\n\nmutation PublisherConnection {\n  publisherConnection {\n    ...Connection\n    __typename\n  }\n}"


class WatchStreamMutation(BaseModel):
    """No documentation found for this operation."""

    watch_stream: Connection = Field(alias="watchStream")
    "What a stream is watched with: its agent's room, where it is the track named by its key. A guest needs the agent in one of their collaborations"

    class Arguments(BaseModel):
        """Arguments for WatchStream"""

        input: WatchStreamInput

    class Meta:
        """Meta class for WatchStream"""

        document = "fragment Connection on Connection {\n  transport\n  credential\n  __typename\n}\n\nmutation WatchStream($input: WatchStreamInput!) {\n  watchStream(input: $input) {\n    ...Connection\n    __typename\n  }\n}"


class WatchAgentMutation(BaseModel):
    """No documentation found for this operation."""

    watch_agent: Connection = Field(alias="watchAgent")
    "What every stream of an agent is watched with. A guest needs the agent in one of their collaborations"

    class Arguments(BaseModel):
        """Arguments for WatchAgent"""

        input: WatchAgentInput

    class Meta:
        """Meta class for WatchAgent"""

        document = "fragment Connection on Connection {\n  transport\n  credential\n  __typename\n}\n\nmutation WatchAgent($input: WatchAgentInput!) {\n  watchAgent(input: $input) {\n    ...Connection\n    __typename\n  }\n}"


class GetAgentQuery(BaseModel):
    """No documentation found for this operation."""

    agent: Agent
    "Get an agent by ID"

    class Arguments(BaseModel):
        """Arguments for GetAgent"""

        id: ID

    class Meta:
        """Meta class for GetAgent"""

        document = "fragment DataFormat on DataFormat {\n  dtype\n  shape\n  unit\n  reference\n  axes {\n    name\n    type\n    __typename\n  }\n  calibration {\n    axis\n    unit\n    scale\n    offset\n    __typename\n  }\n  __typename\n}\n\nfragment Stream on Stream {\n  id\n  key\n  title\n  kind\n  description\n  format {\n    ...DataFormat\n    __typename\n  }\n  agent {\n    id\n    roomName\n    __typename\n  }\n  __typename\n}\n\nfragment Agent on Agent {\n  id\n  name\n  roomName\n  client {\n    clientId\n    __typename\n  }\n  user {\n    sub\n    __typename\n  }\n  streams {\n    ...Stream\n    __typename\n  }\n  __typename\n}\n\nquery GetAgent($id: ID!) {\n  agent(id: $id) {\n    ...Agent\n    __typename\n  }\n}"


class SearchAgentsQueryOptions(BaseModel):
    """An app instance that owns live streams: one per client, user and organization"""

    __identifier__: ClassVar[Literal["@lovekit/agent"]] = "@lovekit/agent"
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

        document = "fragment DataFormat on DataFormat {\n  dtype\n  shape\n  unit\n  reference\n  axes {\n    name\n    type\n    __typename\n  }\n  calibration {\n    axis\n    unit\n    scale\n    offset\n    __typename\n  }\n  __typename\n}\n\nfragment Stream on Stream {\n  id\n  key\n  title\n  kind\n  description\n  format {\n    ...DataFormat\n    __typename\n  }\n  agent {\n    id\n    roomName\n    __typename\n  }\n  __typename\n}\n\nquery GetStream($id: ID!) {\n  stream(id: $id) {\n    ...Stream\n    __typename\n  }\n}"


class IsStreamLiveQueryStream(BaseModel):
    """One live source an agent offers: a camera, a detector, a microphone, a spectrometer"""

    __identifier__: ClassVar[Literal["@lovekit/stream"]] = "@lovekit/stream"
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
    """One live source an agent offers: a camera, a detector, a microphone, a spectrometer"""

    __identifier__: ClassVar[Literal["@lovekit/stream"]] = "@lovekit/stream"
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

        document = "fragment DataFormat on DataFormat {\n  dtype\n  shape\n  unit\n  reference\n  axes {\n    name\n    type\n    __typename\n  }\n  calibration {\n    axis\n    unit\n    scale\n    offset\n    __typename\n  }\n  __typename\n}\n\nfragment Stream on Stream {\n  id\n  key\n  title\n  kind\n  description\n  format {\n    ...DataFormat\n    __typename\n  }\n  agent {\n    id\n    roomName\n    __typename\n  }\n  __typename\n}\n\nquery ListStreams($filter: StreamFilter, $pagination: OffsetPaginationInput) {\n  streams(filters: $filter, pagination: $pagination) {\n    ...Stream\n    __typename\n  }\n}"


class LovekitApi:
    """Every operation of this API as a method. Generated by turms.

    Each method hands its operation to ``execute``, ``aexecute``, ``subscribe``, ``asubscribe`` of ``self``, which the class this one is mixed into (or a base of it) provides.
    """

    __scopes__: ClassVar[tuple[str, ...]] = ("lovekit_publish", "lovekit_watch")

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

    async def apublisher_connection(self) -> Connection:
        """PublisherConnection

        What the caller's agent publishes its streams with; a newer connection replaces an older one

        Args:

        Returns:
            Connection
        """
        variables: dict[str, builtins.object] = {}
        return (
            await self.aexecute(PublisherConnectionMutation, variables)
        ).publisher_connection

    def publisher_connection(self) -> Connection:
        """PublisherConnection

        What the caller's agent publishes its streams with; a newer connection replaces an older one

        Args:

        Returns:
            Connection
        """
        variables: dict[str, builtins.object] = {}
        return self.execute(PublisherConnectionMutation, variables).publisher_connection

    async def awatch_stream(self, stream: IDCoercible) -> Connection:
        """WatchStream

        What a stream is watched with: its agent's room, where it is the track named by its key. A guest needs the agent in one of their collaborations

        Args:
            stream: The `ID` scalar type represents a unique identifier, often used to refetch an object or as key for a cache. The ID type appears in a JSON response as a String; however, it is not intended to be human-readable. When expected as an input type, any string (such as `"4"`) or integer (such as `4`) input value will be accepted as an ID. (required)

        Returns:
            Connection
        """
        variables: dict[str, builtins.object] = {}
        _input: dict[str, builtins.object] = {}
        _input["stream"] = stream
        variables["input"] = _input
        return (await self.aexecute(WatchStreamMutation, variables)).watch_stream

    def watch_stream(self, stream: IDCoercible) -> Connection:
        """WatchStream

        What a stream is watched with: its agent's room, where it is the track named by its key. A guest needs the agent in one of their collaborations

        Args:
            stream: The `ID` scalar type represents a unique identifier, often used to refetch an object or as key for a cache. The ID type appears in a JSON response as a String; however, it is not intended to be human-readable. When expected as an input type, any string (such as `"4"`) or integer (such as `4`) input value will be accepted as an ID. (required)

        Returns:
            Connection
        """
        variables: dict[str, builtins.object] = {}
        _input: dict[str, builtins.object] = {}
        _input["stream"] = stream
        variables["input"] = _input
        return self.execute(WatchStreamMutation, variables).watch_stream

    async def awatch_agent(self, agent: IDCoercible) -> Connection:
        """WatchAgent

        What every stream of an agent is watched with. A guest needs the agent in one of their collaborations

        Args:
            agent: The `ID` scalar type represents a unique identifier, often used to refetch an object or as key for a cache. The ID type appears in a JSON response as a String; however, it is not intended to be human-readable. When expected as an input type, any string (such as `"4"`) or integer (such as `4`) input value will be accepted as an ID. (required)

        Returns:
            Connection
        """
        variables: dict[str, builtins.object] = {}
        _input: dict[str, builtins.object] = {}
        _input["agent"] = agent
        variables["input"] = _input
        return (await self.aexecute(WatchAgentMutation, variables)).watch_agent

    def watch_agent(self, agent: IDCoercible) -> Connection:
        """WatchAgent

        What every stream of an agent is watched with. A guest needs the agent in one of their collaborations

        Args:
            agent: The `ID` scalar type represents a unique identifier, often used to refetch an object or as key for a cache. The ID type appears in a JSON response as a String; however, it is not intended to be human-readable. When expected as an input type, any string (such as `"4"`) or integer (such as `4`) input value will be accepted as an ID. (required)

        Returns:
            Connection
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
