"""App-level browser security headers for Skriptoteket.

Purpose:
    Add a small baseline of response headers that reduce browser-side attack
    surface even when reverse-proxy configuration drifts.

Relationships:
    - Registered by `skriptoteket.web.app.create_app`.
    - Complements, but does not replace, the nginx edge policy in ADR-0021.
"""

from __future__ import annotations

from typing import Final

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class SecurityHeadersMiddleware:
    """Append a minimal browser hardening header set to HTTP responses."""

    _HEADERS: Final[tuple[tuple[bytes, bytes], ...]] = (
        (b"x-frame-options", b"DENY"),
        (b"x-content-type-options", b"nosniff"),
        (b"referrer-policy", b"strict-origin-when-cross-origin"),
        (b"permissions-policy", b"geolocation=(), camera=(), microphone=()"),
    )

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_security_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                message_headers: list[tuple[bytes, bytes]] = list(message.get("headers", []))
                existing = {key.lower() for key, _ in message_headers}
                for header_name, header_value in self._HEADERS:
                    if header_name in existing:
                        continue
                    message_headers.append((header_name, header_value))
                message["headers"] = message_headers

            await send(message)

        await self.app(scope, receive, send_with_security_headers)
