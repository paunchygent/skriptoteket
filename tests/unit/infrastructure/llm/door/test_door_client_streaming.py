"""A streamed door call relays SSE lines, admits the caller and types its failures."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx
import pytest
from pydantic import JsonValue

from skriptoteket.domain.llm_door import (
    AiDailyLimit,
    AiDailyLimitReached,
    AiDoorCaller,
    AiOverageAuthority,
)
from skriptoteket.infrastructure.llm.door import client as door_client
from skriptoteket.protocols.llm_door import DoorOperation, DoorRequestFailed, DoorTimeout
from tests.unit.infrastructure.llm.door.door_client_support import (
    PAYLOAD,
    TEACHER,
    make_door_client,
    refusal_response,
)

SSE_BODY = (
    'event: response.output_text.delta\ndata: {"delta": "Hej"}\n\n'
    'event: response.completed\ndata: {"type": "response.completed"}\n\n'
)
STREAM_PAYLOAD: dict[str, JsonValue] = {**PAYLOAD, "stream": True}


async def test_a_streamed_success_relays_every_line_and_admits_the_caller() -> None:
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200, headers={"content-type": "text/event-stream"}, content=SSE_BODY.encode()
        )

    caller = AiDoorCaller(
        user_id=TEACHER, exempt=True, authority=AiOverageAuthority.JOB_CONTINUATION
    )
    async with make_door_client(httpx.MockTransport(handle)).stream(
        operation=DoorOperation.RESPONSES,
        payload=STREAM_PAYLOAD,
        caller=caller,
        timeout_seconds=5,
    ) as door_stream:
        assert caller.admitted
        lines = [line async for line in door_stream.aiter_lines()]
        assert door_stream.is_success
        assert door_stream.status_code == 200
        assert door_stream.headers["content-type"] == "text/event-stream"

    assert lines == SSE_BODY.splitlines()
    request = seen[0]
    assert request.method == "POST"
    assert str(request.url) == "http://door.test:8080/internal/v1/openai/responses"
    assert json.loads(request.content) == STREAM_PAYLOAD
    assert request.headers["X-Internal-API-Key"] == "internal-key"
    assert request.headers["X-HuleEdu-User-ID"] == str(TEACHER)
    assert request.headers["X-HuleEdu-Exempt-Test-User"] == "true"
    assert request.headers["X-HuleEdu-OpenAI-Allowance-Mode"] == "free_allowance_only"


async def test_a_streamed_limit_429_raises_on_entry_and_leaves_the_caller_not_admitted() -> None:
    caller = AiDoorCaller(
        user_id=TEACHER, exempt=False, authority=AiOverageAuthority.JOB_CONTINUATION
    )
    client = make_door_client(
        httpx.MockTransport(
            lambda request: refusal_response("openai_caller_user_share_exceeded", "user_share")
        )
    )

    with pytest.raises(AiDailyLimitReached) as raised:
        async with client.stream(
            operation=DoorOperation.RESPONSES,
            payload=STREAM_PAYLOAD,
            caller=caller,
            timeout_seconds=5,
        ):
            raise AssertionError("a limit 429 must not open the stream")

    assert raised.value.limit is AiDailyLimit.USER_SHARE
    assert not caller.admitted


async def test_a_streamed_failure_answer_yields_the_body_and_no_lines() -> None:
    caller = AiDoorCaller(
        user_id=TEACHER, exempt=True, authority=AiOverageAuthority.JOB_CONTINUATION
    )
    refusal = httpx.Response(400, json={"error": {"code": "unknown_model"}})
    async with make_door_client(httpx.MockTransport(lambda request: refusal)).stream(
        operation=DoorOperation.RESPONSES,
        payload=STREAM_PAYLOAD,
        caller=caller,
        timeout_seconds=5,
    ) as door_stream:
        lines = [line async for line in door_stream.aiter_lines()]
        assert not door_stream.is_success
        assert door_stream.status_code == 400
        assert json.loads(door_stream.body)["error"]["code"] == "unknown_model"

    assert lines == []
    assert not caller.admitted


async def test_a_streamed_transport_failure_becomes_a_typed_door_error() -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    def refused(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    caller = AiDoorCaller(
        user_id=TEACHER, exempt=True, authority=AiOverageAuthority.JOB_CONTINUATION
    )
    with pytest.raises(DoorTimeout):
        async with make_door_client(httpx.MockTransport(timeout)).stream(
            operation=DoorOperation.RESPONSES,
            payload=STREAM_PAYLOAD,
            caller=caller,
            timeout_seconds=5,
        ):
            raise AssertionError("a timeout must not open the stream")
    with pytest.raises(DoorRequestFailed):
        async with make_door_client(httpx.MockTransport(refused)).stream(
            operation=DoorOperation.RESPONSES,
            payload=STREAM_PAYLOAD,
            caller=caller,
            timeout_seconds=5,
        ):
            raise AssertionError("a refused connection must not open the stream")
    assert not caller.admitted


async def test_a_stream_dying_while_reading_lines_raises_a_typed_door_error() -> None:
    class _DyingBody(httpx.AsyncByteStream):
        async def __aiter__(self) -> AsyncIterator[bytes]:
            yield b"event: response.created\n"
            raise httpx.ReadTimeout("stalled")

    client = make_door_client(
        httpx.MockTransport(lambda request: httpx.Response(200, stream=_DyingBody()))
    )
    caller = AiDoorCaller(
        user_id=TEACHER, exempt=True, authority=AiOverageAuthority.JOB_CONTINUATION
    )
    lines: list[str] = []
    with pytest.raises(DoorTimeout):
        async with client.stream(
            operation=DoorOperation.RESPONSES,
            payload=STREAM_PAYLOAD,
            caller=caller,
            timeout_seconds=5,
        ) as door_stream:
            async for line in door_stream.aiter_lines():
                lines.append(line)

    assert lines == []  # An unfinished SSE event is buffered until its boundary.
    assert caller.admitted


async def test_a_stream_without_charge_record_keeps_missing_charge_warning_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    class _Logger:
        def warning(self, event: str, **_: object) -> None:
            events.append(event)

    monkeypatch.setattr(door_client, "logger", _Logger())
    caller = AiDoorCaller(
        user_id=TEACHER, exempt=False, authority=AiOverageAuthority.JOB_CONTINUATION
    )
    async with make_door_client(
        httpx.MockTransport(lambda request: httpx.Response(200, content=SSE_BODY.encode()))
    ).stream(
        operation=DoorOperation.RESPONSES,
        payload=STREAM_PAYLOAD,
        caller=caller,
        timeout_seconds=5,
    ) as door_stream:
        _ = [line async for line in door_stream.aiter_lines()]

    assert events == ["llm_door_charge_headers_missing"]
    assert caller.admitted
    assert caller.overage_usd_micros == 0
