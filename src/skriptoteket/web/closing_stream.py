"""Deterministic close of a streamed response body.

Purpose:
    Starlette's ``StreamingResponse`` cancels its send task when the client goes
    away but never closes the body iterator, so a generator suspended at a
    ``yield`` stays open until garbage collection. ``ClosingStreamingResponse``
    closes the body it owns when the response ends for any reason, and
    ``anext_unaffected_by_scope_cancel`` lets a body step unwind with one ordinary
    cancellation instead of the repeated cancellation of an AnyIO cancel scope.

Relationships:
    Used by SSE routes whose body generator owns resources (provider streams,
    door slots, in-flight guards, pending turns).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Mapping

import anyio
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse
from starlette.types import Receive, Scope, Send


class ClosingStreamingResponse(StreamingResponse):
    """A streaming response that always closes the body generator it was given."""

    def __init__(
        self,
        content: AsyncGenerator[bytes, None],
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        super().__init__(
            content,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )
        self._owned_body = content

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            # Shielded: the response ends inside a cancelled scope on a client
            # disconnect, and the close awaits the release of the generator's
            # resources (upstream stream, slots, guards, a final turn state).
            with anyio.CancelScope(shield=True):
                await self._owned_body.aclose()


async def anext_unaffected_by_scope_cancel[T](stream: AsyncGenerator[T, None]) -> T:
    """Advance ``stream`` one step in its own task, so cancelling the caller unwinds it once.

    A cancelled AnyIO scope (Starlette's disconnect handling) cancels again at every
    await of the cancelled task, which would interrupt the cleanup the generator runs
    on cancellation. The step task is outside that scope: on cancellation it is
    cancelled once and awaited to completion before the cancellation propagates.
    """

    step = asyncio.ensure_future(anext(stream))
    try:
        return await asyncio.shield(step)
    except asyncio.CancelledError:
        step.cancel()
        with anyio.CancelScope(shield=True):
            await asyncio.wait({step})
        if not step.cancelled():
            step.exception()  # mark it retrieved; the cancellation is what propagates
        raise
