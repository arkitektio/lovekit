from rath.scalars import ID
from lovekit.funcs import execute, aexecute
from typing import Literal, List, Tuple, Optional
from pydantic import BaseModel, Field, ConfigDict
from lovekit.rath import LovekitRath
from enum import Enum


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


class OffsetPaginationInput(BaseModel):
    """No documentation"""

    offset: int
    limit: Optional[int] = None
    model_config = ConfigDict(
        frozen=True, extra="forbid", populate_by_name=True, use_enum_values=True
    )


class CreateStreamInput(BaseModel):
    """No documentation"""

    instance_id: Optional[str] = Field(alias="instanceId", default=None)
    title: Optional[str] = None
    model_config = ConfigDict(
        frozen=True, extra="forbid", populate_by_name=True, use_enum_values=True
    )


class Stream(BaseModel):
    """No documentation"""

    typename: Literal["Stream"] = Field(
        alias="__typename", default="Stream", exclude=True
    )
    id: ID
    token: str
    model_config = ConfigDict(frozen=True)


class CreateVideoStreamMutation(BaseModel):
    """No documentation found for this operation."""

    create_video_stream: Stream = Field(alias="createVideoStream")
    "Create a stream"

    class Arguments(BaseModel):
        """Arguments for CreateVideoStream"""

        input: CreateStreamInput
        model_config = ConfigDict(populate_by_name=True)

    class Meta:
        """Meta class for CreateVideoStream"""

        document = "fragment Stream on Stream {\n  id\n  token\n  __typename\n}\n\nmutation CreateVideoStream($input: CreateStreamInput!) {\n  createVideoStream(input: $input) {\n    ...Stream\n    __typename\n  }\n}"


class GetStreamQuery(BaseModel):
    """No documentation found for this operation."""

    stream: Stream
    "Get a stream by ID"

    class Arguments(BaseModel):
        """Arguments for GetStream"""

        id: ID
        model_config = ConfigDict(populate_by_name=True)

    class Meta:
        """Meta class for GetStream"""

        document = "fragment Stream on Stream {\n  id\n  token\n  __typename\n}\n\nquery GetStream($id: ID!) {\n  stream(id: $id) {\n    ...Stream\n    __typename\n  }\n}"


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

    options: Tuple[SearchStreamsQueryOptions, ...]
    "Get a stream"

    class Arguments(BaseModel):
        """Arguments for SearchStreams"""

        search: Optional[str] = Field(default=None)
        values: Optional[List[ID]] = Field(default=None)
        model_config = ConfigDict(populate_by_name=True)

    class Meta:
        """Meta class for SearchStreams"""

        document = "query SearchStreams($search: String, $values: [ID!]) {\n  options: streams(\n    filters: {search: $search, ids: $values}\n    pagination: {limit: 10}\n  ) {\n    value: id\n    label: title\n    __typename\n  }\n}"


class ListStreamsQuery(BaseModel):
    """No documentation found for this operation."""

    streams: Tuple[Stream, ...]
    "Get a stream"

    class Arguments(BaseModel):
        """Arguments for ListStreams"""

        filter: Optional[StreamFilter] = Field(default=None)
        pagination: Optional[OffsetPaginationInput] = Field(default=None)
        model_config = ConfigDict(populate_by_name=True)

    class Meta:
        """Meta class for ListStreams"""

        document = "fragment Stream on Stream {\n  id\n  token\n  __typename\n}\n\nquery ListStreams($filter: StreamFilter, $pagination: OffsetPaginationInput) {\n  streams(filters: $filter, pagination: $pagination) {\n    ...Stream\n    __typename\n  }\n}"


async def acreate_video_stream(
    instance_id: Optional[str] = None,
    title: Optional[str] = None,
    rath: Optional[LovekitRath] = None,
) -> Stream:
    """CreateVideoStream

    Create a stream

    Args:
        instance_id: The `String` scalar type represents textual data, represented as UTF-8 character sequences. The String type is most often used by GraphQL to represent free-form human-readable text.
        title: The `String` scalar type represents textual data, represented as UTF-8 character sequences. The String type is most often used by GraphQL to represent free-form human-readable text.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        Stream
    """
    return (
        await aexecute(
            CreateVideoStreamMutation,
            {"input": {"instanceId": instance_id, "title": title}},
            rath=rath,
        )
    ).create_video_stream


def create_video_stream(
    instance_id: Optional[str] = None,
    title: Optional[str] = None,
    rath: Optional[LovekitRath] = None,
) -> Stream:
    """CreateVideoStream

    Create a stream

    Args:
        instance_id: The `String` scalar type represents textual data, represented as UTF-8 character sequences. The String type is most often used by GraphQL to represent free-form human-readable text.
        title: The `String` scalar type represents textual data, represented as UTF-8 character sequences. The String type is most often used by GraphQL to represent free-form human-readable text.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        Stream
    """
    return execute(
        CreateVideoStreamMutation,
        {"input": {"instanceId": instance_id, "title": title}},
        rath=rath,
    ).create_video_stream


async def aget_stream(id: ID, rath: Optional[LovekitRath] = None) -> Stream:
    """GetStream

    Get a stream by ID

    Args:
        id (ID): No description
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        Stream
    """
    return (await aexecute(GetStreamQuery, {"id": id}, rath=rath)).stream


def get_stream(id: ID, rath: Optional[LovekitRath] = None) -> Stream:
    """GetStream

    Get a stream by ID

    Args:
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
) -> Tuple[SearchStreamsQueryOptions, ...]:
    """SearchStreams

    Get a stream

    Args:
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
) -> Tuple[SearchStreamsQueryOptions, ...]:
    """SearchStreams

    Get a stream

    Args:
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
) -> Tuple[Stream, ...]:
    """ListStreams

    Get a stream

    Args:
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
) -> Tuple[Stream, ...]:
    """ListStreams

    Get a stream

    Args:
        filter (Optional[StreamFilter], optional): No description.
        pagination (Optional[OffsetPaginationInput], optional): No description.
        rath (lovekit.rath.LovekitRath, optional): The client we want to use (defaults to the currently active client)

    Returns:
        List[Stream]
    """
    return execute(
        ListStreamsQuery, {"filter": filter, "pagination": pagination}, rath=rath
    ).streams


StreamFilter.model_rebuild()
