"""Editor streams take the door client's bounded pool and slots (41-01-04 review F5).

A streamed call holds its door slots until the stream closes, retries a
capacity 429 on open as ``send`` does, and ends a pooled-connection wait as
``AiDoorBusy``. The production DI hands every editor provider the one door
client whose pool is sized from ``LLM_DOOR_MAX_CONNECTIONS``.
"""

from __future__ import annotations

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
    ChatOpsProviderProtocol,
    ChatStreamProviderProtocol,
    InlineCompletionProviderProtocol,
)
from skriptoteket.protocols.llm_door import DoorOperation, LlmDoorClientProtocol
from skriptoteket.protocols.sleeper import SleeperProtocol

PAYLOAD: dict[str, JsonValue] = {"model": "gpt-6.1-sol", "input": "hej", "stream": True}
CAPACITY_BODY = {"error": {"type": "huleedu_openai_door", "code": "openai_door_admission_full"}}
SSE = b'event: response.output_text.delta\ndata: {"delta": "hej"}\n\n'


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


def _pool_max_connections(door: LlmDoorClientProtocol) -> int:
    assert isinstance(door, HuleEduLlmDoorClient)
    transport = door._client._transport  # noqa: SLF001 - the wiring under test
    assert isinstance(transport, httpx.AsyncHTTPTransport)
    return transport._pool._max_connections  # noqa: SLF001


@pytest.mark.unit
async def test_every_editor_provider_gets_the_door_client_with_the_sized_pool() -> None:
    settings = Settings(
        HULEEDU_LLM_PROVIDER_BASE_URL="http://door.test:8080",
        HULEEDU_INTERNAL_API_KEY="internal-key",
        LLM_DOOR_MAX_CONNECTIONS=260,
    )
    container = make_async_container(LlmProvider(), _Runtime(settings), skip_validation=True)
    try:
        door = await container.get(LlmDoorClientProtocol)
        providers: list[object] = [
            await container.get(ChatStreamProviderProtocol),
            await container.get(ChatOpsProviderProtocol),
            await container.get(InlineCompletionProviderProtocol),
        ]

        assert _pool_max_connections(door) == 260
        assert all(provider._door is door for provider in providers)  # type: ignore[attr-defined]  # noqa: SLF001
    finally:
        await container.close()
