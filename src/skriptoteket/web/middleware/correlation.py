from __future__ import annotations

from typing import Final
from uuid import UUID, uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send
from structlog.contextvars import bind_contextvars, clear_contextvars


def _extract_correlation_id(headers: list[tuple[bytes, bytes]]) -> UUID:
    for name, value in headers:
        if name.lower() != b"x-correlation-id":
            continue

        raw_value = value.decode("latin-1").strip()
        if not raw_value:
            return uuid4()

        try:
            return UUID(raw_value)
        except ValueError:
            return uuid4()

    return uuid4()


class CorrelationMiddleware:
    """Bind per-request correlation ID for structured logs and response headers.

    Pure ASGI middleware (not BaseHTTPMiddleware) so correlation remains available
    when the server emits `uvicorn.access` logs at `http.response.start` and during
    streaming responses.
    """

    header_name: Final[str] = "X-Correlation-ID"
    _header_name_bytes: Final[bytes] = b"x-correlation-id"

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers: list[tuple[bytes, bytes]] = list(scope.get("headers", []))
        correlation_id = _extract_correlation_id(headers)

        scope.setdefault("state", {})["correlation_id"] = correlation_id

        clear_contextvars()
        bind_contextvars(correlation_id=str(correlation_id))

        header_value = str(correlation_id).encode("ascii")
        header_name = self._header_name_bytes

        async def send_with_correlation(message: Message) -> None:
            if message["type"] == "http.response.start":
                message_headers: list[tuple[bytes, bytes]] = list(message.get("headers", []))
                message_headers = [(k, v) for (k, v) in message_headers if k.lower() != header_name]
                message_headers.append((header_name, header_value))
                message["headers"] = message_headers

            await send(message)

        try:
            await self.app(scope, receive, send_with_correlation)
        finally:
            clear_contextvars()
