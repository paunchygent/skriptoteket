"""Editor streams take the door client's bounded pool and slots (41-01-04 review F5).

A streamed call holds its door slots until the stream closes, retries a
capacity 429 on open as ``send`` does, and ends a pooled-connection wait as
``AiDoorBusy``. In the production DI every editor provider calls through the one
door client whose transport is built with ``LLM_DOOR_MAX_CONNECTIONS``.
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import TypedDict, Unpack
from uuid import uuid4

import httpx
import pytest
from dishka import Provider, Scope, make_async_container, provide
from pydantic import JsonValue

from skriptoteket.config import Settings
from skriptoteket.di.llm import LlmProvider
from skriptoteket.domain.llm_door import AiDoorBusy, AiDoorCaller, AiOverageAuthority
from skriptoteket.infrastructure.llm.door.client import DoorBounds, HuleEduLlmDoorClient
from skriptoteket.protocols.llm import (
    ChatMessage,
    ChatOpsProviderProtocol,
    ChatStreamProviderProtocol,
    InlineCompletionProviderProtocol,
    LLMChatRequest,
    LLMCompletionRequest,
)
from skriptoteket.protocols.llm_door import DoorOperation
from skriptoteket.protocols.sleeper import SleeperProtocol

PAYLOAD: dict[str, JsonValue] = {"model": "gpt-6.1-sol", "input": "hej", "stream": True}
CAPACITY_BODY = {"error": {"type": "huleedu_openai_door", "code": "openai_door_admission_full"}}
SSE = (
    b"event: response.output_text.delta\n"
    b'data: {"type": "response.output_text.delta", "delta": "hej"}\n\n'
    b"event: response.completed\n"
    b'data: {"type": "response.completed"}\n\n'
)
COMPLETED: dict[str, JsonValue] = {
    "status": "completed",
    "output": [
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "done"}],
        }
    ],
}
CHAT_REQUEST = LLMChatRequest(messages=[ChatMessage(role="user", content="hej")])
COMPLETION_REQUEST = LLMCompletionRequest(prefix="def f(", suffix=")", active_file="tool.py")


class BoundOverrides(TypedDict, total=False):
    max_in_flight: int
    slot_wait_seconds: float
    capacity_retries: int


class RecordingSleeper:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def sleep(self, seconds: float) -> None:
        self.delays.append(seconds)


def _client(
    handler: httpx.MockTransport,
    *,
    sleeper: RecordingSleeper | None = None,
    **bounds: Unpack[BoundOverrides],
) -> HuleEduLlmDoorClient:
    return HuleEduLlmDoorClient(
        client=httpx.AsyncClient(transport=handler),
        base_url="http://door.test:8080",
        internal_api_key="internal-key",
        job_overage_cap_usd_micros=1_000_000,
        sleeper=sleeper or RecordingSleeper(),
        bounds=replace(DoorBounds.from_settings(Settings()), **bounds),
    )


def _caller() -> AiDoorCaller:
    return AiDoorCaller(user_id=uuid4(), exempt=True, authority=AiOverageAuthority.JOB_CONTINUATION)


def _sse(_: httpx.Request) -> httpx.Response:
    return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=SSE)


@pytest.mark.unit
async def test_an_open_stream_holds_its_process_slot_until_it_closes() -> None:
    client = _client(httpx.MockTransport(_sse), max_in_flight=1, slot_wait_seconds=0.01)

    async with client.stream(
        operation=DoorOperation.RESPONSES, payload=PAYLOAD, caller=_caller(), timeout_seconds=5
    ) as stream:
        assert stream.is_success
        with pytest.raises(AiDoorBusy):
            await client.send(
                operation=DoorOperation.RESPONSES,
                payload=PAYLOAD,
                caller=_caller(),
                timeout_seconds=5,
            )
        assert [line async for line in stream.aiter_lines()][0].startswith("event:")

    reply = await client.send(
        operation=DoorOperation.RESPONSES, payload=PAYLOAD, caller=_caller(), timeout_seconds=5
    )
    assert reply.status_code == 200


@pytest.mark.unit
async def test_a_stream_waiting_for_a_full_process_ends_as_busy() -> None:
    client = _client(httpx.MockTransport(_sse), max_in_flight=1, slot_wait_seconds=0.01)

    async with client.stream(
        operation=DoorOperation.RESPONSES, payload=PAYLOAD, caller=_caller(), timeout_seconds=5
    ):
        with pytest.raises(AiDoorBusy):
            async with client.stream(
                operation=DoorOperation.RESPONSES,
                payload=PAYLOAD,
                caller=_caller(),
                timeout_seconds=5,
            ):
                pass


@pytest.mark.unit
async def test_a_capacity_429_on_open_is_resent_after_its_retry_after() -> None:
    answers = iter(
        [
            httpx.Response(429, headers={"Retry-After": "2"}, json=CAPACITY_BODY),
            httpx.Response(200, headers={"content-type": "text/event-stream"}, content=SSE),
        ]
    )
    sleeper = RecordingSleeper()
    client = _client(
        httpx.MockTransport(lambda _: next(answers)), sleeper=sleeper, capacity_retries=1
    )
    caller = _caller()

    async with client.stream(
        operation=DoorOperation.RESPONSES, payload=PAYLOAD, caller=caller, timeout_seconds=5
    ) as stream:
        assert stream.is_success

    assert sleeper.delays == [2.0]
    assert caller.admitted


@pytest.mark.unit
async def test_a_door_still_full_on_open_after_the_retries_ends_as_busy() -> None:
    client = _client(
        httpx.MockTransport(lambda _: httpx.Response(429, json=CAPACITY_BODY)), capacity_retries=1
    )

    with pytest.raises(AiDoorBusy):
        async with client.stream(
            operation=DoorOperation.RESPONSES, payload=PAYLOAD, caller=_caller(), timeout_seconds=5
        ):
            pass


@pytest.mark.unit
async def test_an_exhausted_connection_pool_on_open_is_busy() -> None:
    def pool_exhausted(request: httpx.Request) -> httpx.Response:
        raise httpx.PoolTimeout("no free connection", request=request)

    client = _client(httpx.MockTransport(pool_exhausted))

    with pytest.raises(AiDoorBusy):
        async with client.stream(
            operation=DoorOperation.RESPONSES, payload=PAYLOAD, caller=_caller(), timeout_seconds=5
        ):
            pass


class _Runtime(Provider):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._settings = settings

    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        return self._settings

    @provide(scope=Scope.APP)
    def sleeper(self) -> SleeperProtocol:
        return RecordingSleeper()


class _RecordedTransports:
    """Stands in for ``httpx.AsyncHTTPTransport``: records each one built and every request.

    Every request is answered as the door would: an SSE stream for a streamed body,
    otherwise one completed Responses answer.
    """

    def __init__(self) -> None:
        self.limits: list[httpx.Limits] = []
        self.requests: list[httpx.Request] = []

    def __call__(self, *, limits: httpx.Limits) -> httpx.AsyncBaseTransport:
        self.limits.append(limits)
        return httpx.MockTransport(self._answer)

    def _answer(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if json.loads(request.content).get("stream"):
            return _sse(request)
        return httpx.Response(200, json=COMPLETED)


@pytest.mark.unit
async def test_every_editor_provider_calls_through_the_door_client_with_the_sized_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transports = _RecordedTransports()
    monkeypatch.setattr(httpx, "AsyncHTTPTransport", transports)
    settings = Settings(
        HULEEDU_LLM_PROVIDER_BASE_URL="http://door.test:8080",
        HULEEDU_INTERNAL_API_KEY="internal-key",
        LLM_DOOR_MAX_CONNECTIONS=260,
    )
    container = make_async_container(LlmProvider(), _Runtime(settings), skip_validation=True)
    try:
        completion = await container.get(InlineCompletionProviderProtocol)
        chat_ops = await container.get(ChatOpsProviderProtocol)
        chat_stream = await container.get(ChatStreamProviderProtocol)

        await completion.complete_inline(
            request=COMPLETION_REQUEST, system_prompt="sys", caller=_caller()
        )
        await chat_ops.complete_chat_ops(
            request=CHAT_REQUEST, system_prompt="sys", caller=_caller()
        )
        deltas = [
            delta
            async for delta in chat_stream.stream_chat(
                request=CHAT_REQUEST, system_prompt="sys", caller=_caller()
            )
        ]
    finally:
        await container.close()

    assert [limits.max_connections for limits in transports.limits] == [260]
    assert deltas == ["hej"]
    assert len(transports.requests) == 3
    assert {request.url.host for request in transports.requests} == {"door.test"}
