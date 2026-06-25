"""Lightweight initialization tests that need no deployed stack.

These carry no ``integration`` marker, so they run on every OS in the CI matrix,
exercising pure-Python construction of the client and the generated schema models.
"""

from lovekit.lovekit import Lovekit
from lovekit.api.schema import (
    EnsureStreamInput,
    OffsetPaginationInput,
    StreamFilter,
    StreamKind,
)


def test_lovekit_importable() -> None:
    """The top-level ``Lovekit`` composition imports and is a class."""
    assert isinstance(Lovekit, type)


def test_stream_kind_values() -> None:
    """The ``StreamKind`` enum exposes the expected members."""
    assert StreamKind.VIDEO.value == "VIDEO"
    assert StreamKind.AUDIO.value == "AUDIO"


def test_ensure_stream_input_constructs() -> None:
    """``EnsureStreamInput`` builds from a kind and title."""
    payload = EnsureStreamInput(kind=StreamKind.VIDEO, title="hello")
    assert payload.kind == StreamKind.VIDEO.value
    assert payload.title == "hello"


def test_offset_pagination_input_constructs() -> None:
    """``OffsetPaginationInput`` builds from plain values."""
    pagination = OffsetPaginationInput(offset=0, limit=5)
    assert pagination.offset == 0
    assert pagination.limit == 5


def test_stream_filter_defaults_to_empty() -> None:
    """``StreamFilter`` is fully optional and constructs with no arguments."""
    assert StreamFilter().model_dump(exclude_none=True) == {}
