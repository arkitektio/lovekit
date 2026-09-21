"""A lovekit call goes through the client it is made on, and nothing else.

No server: the rath is a fake returning canned data.
"""

import importlib
from types import SimpleNamespace
from typing import Any, AsyncIterator, Optional

import pytest
from koil import Koil
from pydantic import BaseModel, ConfigDict
from rath.origin import ContextBound, get_origin

from lovekit.api import schema
from lovekit.lovekit import Lovekit


class FakeRath:
    """Answers every query with the same canned stream, and remembers what was sent."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    def _answer(self, variables: dict[str, Any]) -> Any:
        self.sent.append(variables)
        return SimpleNamespace(
            data={"stream": {"id": "stream-1", "__typename": "Stream", "broadcast": {"id": "b-1"}}}
        )

    async def aquery(self, document: str, variables: dict[str, Any]) -> Any:
        return self._answer(variables)

    async def asubscribe(self, document: str, variables: dict[str, Any]) -> AsyncIterator[Any]:
        yield self._answer(variables)


class Broadcast(ContextBound):
    model_config = ConfigDict(frozen=True)
    id: str


class BoundStream(ContextBound):
    model_config = ConfigDict(frozen=True)
    id: str
    broadcast: Broadcast


class GetBoundStream(BaseModel):
    """Shaped like a generated operation, with models that remember their origin."""

    stream: BoundStream

    class Arguments(BaseModel):
        id: str
        note: Optional[str] = None

    class Meta:
        document = "query GetStream($id: ID!) { stream(id: $id) { id } }"


def client() -> Lovekit:
    """The real client over a fake transport (the field is typed LovekitRath)."""
    return Lovekit.model_construct(rath=FakeRath())


# --------------------------------------------------------------------------- #
# The client's own execute methods
# --------------------------------------------------------------------------- #


async def test_aexecute_goes_through_the_client_and_results_remember_it() -> None:
    mine, other = client(), client()

    result = await mine.aexecute(GetBoundStream, {"id": "stream-1"})

    assert (len(mine.rath.sent), len(other.rath.sent)) == (1, 0)
    origin = get_origin(result.stream.broadcast)
    assert origin is not None and origin.client is mine and origin.rath is mine.rath


def test_execute_goes_through_the_client() -> None:
    mine = client()
    with Koil():
        assert mine.execute(GetBoundStream, {"id": "stream-1"}).stream.id == "stream-1"
    assert len(mine.rath.sent) == 1


async def test_asubscribe_goes_through_the_client() -> None:
    mine = client()
    events = [e async for e in mine.asubscribe(GetBoundStream, {"id": "stream-1"})]
    assert [e.stream.id for e in events] == ["stream-1"]
    assert get_origin(events[0].stream).client is mine


async def test_unset_arguments_are_still_sent() -> None:
    """lovekit's wire behaviour, kept through the rewrite: no exclude_unset."""
    mine = client()
    await mine.aexecute(GetBoundStream, {"id": "stream-1"})
    assert mine.rath.sent == [{"id": "stream-1", "note": None}]


def test_the_executor_is_the_client_and_takes_nothing_else() -> None:
    import inspect

    mine = client()
    for fn in (mine.execute, mine.aexecute, mine.subscribe, mine.asubscribe):
        assert list(inspect.signature(fn).parameters) == ["operation", "variables"]


# --------------------------------------------------------------------------- #
# The generated operations are the client's methods
# --------------------------------------------------------------------------- #


async def test_a_generated_method_goes_through_its_own_client() -> None:
    mine, other = client(), client()

    stream = await mine.aget_stream("stream-1")

    assert isinstance(stream, schema.Stream) and stream.id == "stream-1"
    assert (len(mine.rath.sent), len(other.rath.sent)) == (1, 0)
    assert mine.rath.sent == [{"id": "stream-1"}]


def test_a_sync_generated_method_goes_through_its_own_client() -> None:
    mine = client()
    with Koil():
        assert mine.get_stream("stream-1").id == "stream-1"
    assert len(mine.rath.sent) == 1


def test_operations_are_methods_not_module_functions() -> None:
    assert issubclass(Lovekit, schema.LovekitApi)
    for name in ("aget_stream", "get_stream", "aensure_stream", "list_streams"):
        assert callable(getattr(Lovekit, name))
        assert not hasattr(schema, name), f"{name} is still a module-level function"
    assert set(Lovekit.model_fields) == {"rath"}


def test_there_is_no_ambient_lookup_module() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("lovekit.vars")
