"""The core client for the lovekit service"""

from collections.abc import AsyncGenerator, AsyncIterator, Generator, Iterable
from typing import TYPE_CHECKING, Any

from fakts import Alias
from koil import unkoil, unkoil_gen
from koil.composition import Composition
from pydantic import PrivateAttr
from rath.origin import origin_context
from rath.turms.funcs import TOperation

from lovekit.api.schema import LovekitApi
from lovekit.rath import LovekitRath

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from lovekit.api.schema import Stream
    from lovekit.frames import Frame
    from lovekit.publish import Declaration, LiveStreams


class Lovekit(Composition, LovekitApi):
    """Lovekit

    Every lovekit operation is a method of it (``lovekit.aget_stream(id)``), mixed
    in from the generated ``LovekitApi``. Each of those hands its operation class
    and variables to ``execute``/``aexecute`` (queries and mutations) or
    ``subscribe``/``asubscribe`` (subscriptions) below, which run it over ``rath``.
    Nothing is looked up; what a call returns remembers the client it was called on.
    Actions ask for it by annotation (``lovekit: Lovekit``) and are handed their
    app's client.
    """

    rath: LovekitRath
    livekit: Alias | None = None
    """The media server rooms are hosted on, as resolved: a mesh alias carries
    the mesh node it is reached through."""
    _publisher: Any = PrivateAttr(default=None)

    def publish(self, streams: "Iterable[Declaration]") -> "LiveStreams":
        """Offer exactly these streams as this app's agent, and keep them published.

        ``async with lovekit.publish([VideoStream("camera")]) as live:`` declares them,
        joins as the agent's publisher (again, whenever the connection drops) and gives the
        tracks to send to (``live.video("camera")``). See :mod:`lovekit.publish`.

        The declaration is the agent's whole set, so a client publishes once at a time:
        a second ``publish`` while the first is open raises.
        """
        from lovekit.publish import LiveStreams, declarations

        if self._publisher is not None:
            raise RuntimeError(
                "This client already publishes its agent's streams: declare them all in one publish()"
            )
        live = LiveStreams(self, declarations(streams))
        self._publisher = live
        return live

    def watch(
        self, stream: "Stream"
    ) -> "AbstractAsyncContextManager[AsyncIterator[Frame]]":
        """The frames of a data stream another app publishes.

        ``async with lovekit.watch(stream) as frames:`` joins through whatever carries the
        stream (also over the mesh) and gives its frames, newest only. See :mod:`lovekit.watch`.
        """
        from lovekit.watch import watch

        return watch(self, stream)

    def _release_publisher(self, live: "LiveStreams") -> None:
        if self._publisher is live:
            self._publisher = None

    def _serialize(
        self, operation: type[TOperation], variables: dict[str, Any]
    ) -> dict[str, Any]:
        # lovekit sends every argument, set or not (no exclude_unset), as it always has.
        return operation.Arguments(**variables).model_dump(by_alias=True)

    def execute(
        self, operation: type[TOperation], variables: dict[str, Any]
    ) -> TOperation:
        """Executes a query or mutation in a blocking way."""
        return unkoil(self.aexecute, operation, variables)

    async def aexecute(
        self, operation: type[TOperation], variables: dict[str, Any]
    ) -> TOperation:
        """Executes a query or mutation in a non-blocking way."""
        x = await self.rath.aquery(
            operation.Meta.document, self._serialize(operation, variables)
        )
        return operation.model_validate(
            x.data, context=origin_context(client=self, rath=self.rath)
        )

    def subscribe(
        self, operation: type[TOperation], variables: dict[str, Any]
    ) -> Generator[TOperation, None, None]:
        """Subscribes to an operation in a blocking way."""
        return unkoil_gen(self.asubscribe, operation, variables)

    async def asubscribe(
        self, operation: type[TOperation], variables: dict[str, Any]
    ) -> AsyncGenerator[TOperation, None]:
        """Subscribes to an operation in a non-blocking way."""
        async for event in self.rath.asubscribe(
            operation.Meta.document, self._serialize(operation, variables)
        ):
            yield operation.model_validate(
                event.data, context=origin_context(client=self, rath=self.rath)
            )
