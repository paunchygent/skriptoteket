from __future__ import annotations

import asyncio
import io
import json
import logging
from collections.abc import Callable
from typing import cast
from uuid import UUID

import pytest
import structlog
from starlette.types import Message, Receive, Scope, Send
from structlog.contextvars import clear_contextvars, get_contextvars
from structlog.processors import JSONRenderer
from structlog.stdlib import ProcessorFormatter

from skriptoteket.web.middleware.correlation import CorrelationMiddleware


def _capture_uvicorn_access_json() -> tuple[io.StringIO, Callable[[], None]]:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(
        ProcessorFormatter(
            processor=JSONRenderer(),
            foreign_pre_chain=[structlog.contextvars.merge_contextvars],
        )
    )

    logger = logging.getLogger("uvicorn.access")
    old_handlers = list(logger.handlers)
    old_level = logger.level
    old_propagate = logger.propagate
    old_disabled = logger.disabled
    old_filters = list(logger.filters)

    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.disabled = False
    logger.filters = []

    def restore() -> None:
        logger.handlers = old_handlers
        logger.propagate = old_propagate
        logger.setLevel(old_level)
        logger.disabled = old_disabled
        logger.filters = old_filters

    return stream, restore


def _http_scope(*, headers: dict[str, str] | None = None) -> Scope:
    raw_headers: list[tuple[bytes, bytes]] = []
    for key, value in (headers or {}).items():
        raw_headers.append((key.lower().encode("ascii"), value.encode("ascii")))

    return cast(
        Scope,
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/healthz",
            "raw_path": b"/healthz",
            "query_string": b"",
            "headers": raw_headers,
            "client": ("127.0.0.1", 12345),
            "server": ("test", 80),
        },
    )


async def _receive() -> Message:
    return {"type": "http.request", "body": b"", "more_body": False}


def _get_header(headers: list[tuple[bytes, bytes]], name: bytes) -> bytes | None:
    for k, v in headers:
        if k.lower() == name:
            return v
    return None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_valid_inbound_id_echoed_in_response_and_access_log() -> None:
    clear_contextvars()

    requested = UUID("72d70ad9-0265-4e7e-94b8-cd0753c87b79")
    scope = _http_scope(headers={"X-Correlation-ID": str(requested)})

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"x-correlation-id", b"downstream-wrong")],
            }
        )
        await send({"type": "http.response.body", "body": b"ok", "more_body": False})

    middleware = CorrelationMiddleware(app)
    stream, restore = _capture_uvicorn_access_json()

    response_start: Message | None = None

    async def send(message: Message) -> None:
        nonlocal response_start
        if message["type"] == "http.response.start":
            response_start = message
            logging.getLogger("uvicorn.access").info('127.0.0.1 - "GET /healthz HTTP/1.1" 200')

    try:
        await middleware(scope, _receive, send)
    finally:
        restore()

    assert scope["state"]["correlation_id"] == requested
    assert response_start is not None
    assert _get_header(response_start["headers"], b"x-correlation-id") == str(requested).encode(
        "ascii"
    )

    log_lines = stream.getvalue().splitlines()
    assert len(log_lines) == 1
    payload = json.loads(log_lines[0])
    assert payload["correlation_id"] == str(requested)
    assert get_contextvars() == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_missing_inbound_id_generates_and_logs_uuid() -> None:
    clear_contextvars()

    scope = _http_scope()

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok", "more_body": False})

    middleware = CorrelationMiddleware(app)
    stream, restore = _capture_uvicorn_access_json()

    response_start: Message | None = None

    async def send(message: Message) -> None:
        nonlocal response_start
        if message["type"] == "http.response.start":
            response_start = message
            logging.getLogger("uvicorn.access").info('127.0.0.1 - "GET /healthz HTTP/1.1" 200')

    try:
        await middleware(scope, _receive, send)
    finally:
        restore()

    assert response_start is not None
    header_value = _get_header(response_start["headers"], b"x-correlation-id")
    assert header_value is not None

    generated = UUID(header_value.decode("ascii"))
    assert scope["state"]["correlation_id"] == generated

    payload = json.loads(stream.getvalue().splitlines()[0])
    assert payload["correlation_id"] == str(generated)
    assert get_contextvars() == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_invalid_inbound_id_generates_and_logs_uuid() -> None:
    clear_contextvars()

    scope = _http_scope(headers={"X-Correlation-ID": "not-a-uuid"})

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok", "more_body": False})

    middleware = CorrelationMiddleware(app)
    stream, restore = _capture_uvicorn_access_json()

    response_start: Message | None = None

    async def send(message: Message) -> None:
        nonlocal response_start
        if message["type"] == "http.response.start":
            response_start = message
            logging.getLogger("uvicorn.access").info('127.0.0.1 - "GET /healthz HTTP/1.1" 200')

    try:
        await middleware(scope, _receive, send)
    finally:
        restore()

    assert response_start is not None
    header_value = _get_header(response_start["headers"], b"x-correlation-id")
    assert header_value is not None

    generated = UUID(header_value.decode("ascii"))
    assert scope["state"]["correlation_id"] == generated

    payload = json.loads(stream.getvalue().splitlines()[0])
    assert payload["correlation_id"] == str(generated)
    assert get_contextvars() == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_streaming_keeps_context_until_completion_and_clears_after() -> None:
    clear_contextvars()

    requested = UUID("9a8e3d66-8844-4625-bb92-cfa080ea362c")
    scope = _http_scope(headers={"X-Correlation-ID": str(requested)})

    observed: dict[str, str | None] = {}

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        observed["before_start"] = get_contextvars().get("correlation_id")
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"chunk1", "more_body": True})
        observed["after_chunk1"] = get_contextvars().get("correlation_id")
        await send({"type": "http.response.body", "body": b"chunk2", "more_body": False})
        observed["after_final"] = get_contextvars().get("correlation_id")

    middleware = CorrelationMiddleware(app)
    stream, restore = _capture_uvicorn_access_json()

    async def send(message: Message) -> None:
        if message["type"] == "http.response.start":
            logging.getLogger("uvicorn.access").info('127.0.0.1 - "GET /healthz HTTP/1.1" 200')

    try:
        await middleware(scope, _receive, send)
    finally:
        restore()

    assert observed == {
        "before_start": str(requested),
        "after_chunk1": str(requested),
        "after_final": str(requested),
    }
    payload = json.loads(stream.getvalue().splitlines()[0])
    assert payload["correlation_id"] == str(requested)
    assert get_contextvars() == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_concurrent_requests_do_not_leak_contextvars() -> None:
    clear_contextvars()

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok", "more_body": False})

    middleware = CorrelationMiddleware(app)
    stream, restore = _capture_uvicorn_access_json()

    async def run_request(correlation_id: UUID) -> bytes:
        scope = _http_scope(headers={"X-Correlation-ID": str(correlation_id)})
        response_start: Message | None = None

        async def send(message: Message) -> None:
            nonlocal response_start
            if message["type"] == "http.response.start":
                response_start = message
                logging.getLogger("uvicorn.access").info('127.0.0.1 - "GET /healthz HTTP/1.1" 200')

        await middleware(scope, _receive, send)
        assert response_start is not None
        header_value = _get_header(response_start["headers"], b"x-correlation-id")
        assert header_value is not None
        return header_value

    a = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    b = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

    try:
        returned_a, returned_b = await asyncio.gather(run_request(a), run_request(b))
    finally:
        restore()

    assert returned_a == str(a).encode("ascii")
    assert returned_b == str(b).encode("ascii")

    observed_ids = {json.loads(line)["correlation_id"] for line in stream.getvalue().splitlines()}
    assert observed_ids == {str(a), str(b)}
    assert get_contextvars() == {}
