"""Private stream settlement reuses caller charging without altering provider SSE."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

import httpx
import pytest

from skriptoteket.domain.llm_door import AiJobOverageCapReached
from skriptoteket.protocols.llm_door import DoorOperation
from tests.unit.infrastructure.llm.door.door_client_support import make_door_client
from tests.unit.infrastructure.llm.door.test_door_client_streaming import SSE_BODY, STREAM_PAYLOAD
from tests.unit.llm_door_fakes import fixture_caller, sse_reply


def _charge(micros: object = 7, kind: str = "overage") -> bytes:
    return (
        "event: huleedu.door.charge\ndata: "
        + json.dumps(
            {"type": "huleedu.door.charge", "charge_kind": kind, "charge_usd_micros": micros}
        )
        + "\n\n"
    ).encode()


@pytest.mark.parametrize("read_all", [True, False])
async def test_late_charge_after_provider_terminal_is_hidden_and_recorded_once(
    read_all: bool,
) -> None:
    caller = fixture_caller(exempt=False)
    body = SSE_BODY.encode() + _charge() + _charge()  # Duplicate metadata is not a second call.
    client = make_door_client(
        httpx.MockTransport(lambda request: httpx.Response(200, content=body))
    )
    lines: list[str] = []
    async with client.stream(
        operation=DoorOperation.RESPONSES, payload=STREAM_PAYLOAD, caller=caller, timeout_seconds=5
    ) as stream:
        async for line in stream.aiter_lines():
            lines.append(line)
            if not read_all and line.startswith("data:") and "response.completed" in line:
                break
    assert caller.overage_usd_micros == 7
    assert lines == (SSE_BODY.splitlines() if read_all else SSE_BODY.splitlines()[:-1])


async def test_charge_crossing_existing_cap_prevents_success_even_on_early_completion() -> None:
    caller = fixture_caller(exempt=False)
    client = make_door_client(
        httpx.MockTransport(
            lambda request: httpx.Response(200, content=SSE_BODY.encode() + _charge(1_000_001))
        )
    )
    with pytest.raises(AiJobOverageCapReached):
        async with client.stream(
            operation=DoorOperation.RESPONSES,
            payload=STREAM_PAYLOAD,
            caller=caller,
            timeout_seconds=5,
        ) as stream:
            async for line in stream.aiter_lines():
                if "response.completed" in line:
                    break
    assert caller.overage_usd_micros == 1_000_001
    # The already-recorded charge also fences a subsequent call on the same job.
    with pytest.raises(AiJobOverageCapReached):
        async with client.stream(
            operation=DoorOperation.RESPONSES,
            payload=STREAM_PAYLOAD,
            caller=caller,
            timeout_seconds=5,
        ):
            raise AssertionError("the next call must not open")


@pytest.mark.parametrize(
    "kind,micros", [("complimentary", 0), ("overage", 0), ("overage", 1_000_000)]
)
async def test_complimentary_zero_and_exact_cap_use_existing_charge_policy(
    kind: str, micros: int
) -> None:
    caller = fixture_caller(exempt=False)
    client = make_door_client(
        httpx.MockTransport(
            lambda request: httpx.Response(200, content=SSE_BODY.encode() + _charge(micros, kind))
        )
    )
    async with client.stream(
        operation=DoorOperation.RESPONSES, payload=STREAM_PAYLOAD, caller=caller, timeout_seconds=5
    ) as stream:
        assert [line async for line in stream.aiter_lines()] == SSE_BODY.splitlines()
    assert caller.overage_usd_micros == micros


@pytest.mark.parametrize("exempt", [True, False])
@pytest.mark.parametrize(
    "wire", [b"", _charge(True), _charge(-1), _charge("7"), _charge(2, "unknown")]
)
async def test_missing_or_invalid_charge_keeps_no_charge_policy(
    exempt: bool, wire: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    from skriptoteket.infrastructure.llm.door import client as door_client

    warnings: list[str] = []

    class Logger:
        def warning(self, event: str, **_: object) -> None:
            warnings.append(event)

    monkeypatch.setattr(door_client, "logger", Logger())
    caller = fixture_caller(exempt=exempt)
    client = make_door_client(
        httpx.MockTransport(lambda request: httpx.Response(200, content=SSE_BODY.encode() + wire))
    )
    async with client.stream(
        operation=DoorOperation.RESPONSES, payload=STREAM_PAYLOAD, caller=caller, timeout_seconds=5
    ) as stream:
        assert [line async for line in stream.aiter_lines()] == SSE_BODY.splitlines()
    assert caller.overage_usd_micros == 0
    assert warnings == ([] if exempt else ["llm_door_charge_headers_missing"])


@pytest.mark.parametrize("error_type", [RuntimeError, asyncio.CancelledError, GeneratorExit])
async def test_exceptional_consumer_exit_closes_without_draining_provider(
    error_type: type[BaseException],
) -> None:
    closed = False
    read_past_first_event = False

    class Body(httpx.AsyncByteStream):
        async def __aiter__(self) -> AsyncIterator[bytes]:
            nonlocal read_past_first_event
            yield sse_reply([("response.created", {"type": "response.created"})]).body
            read_past_first_event = True
            raise AssertionError("exceptional consumer exit must not read the provider tail")

        async def aclose(self) -> None:
            nonlocal closed
            closed = True

    client = make_door_client(
        httpx.MockTransport(lambda request: httpx.Response(200, stream=Body()))
    )
    with pytest.raises(error_type):
        async with client.stream(
            operation=DoorOperation.RESPONSES,
            payload=STREAM_PAYLOAD,
            caller=fixture_caller(),
            timeout_seconds=5,
        ) as stream:
            async for _ in stream.aiter_lines():
                raise error_type()
    assert closed
    assert not read_past_first_event


@pytest.mark.parametrize("read_all", [True, False])
async def test_task_cancellation_closes_active_read_or_normal_exit_drain(read_all: bool) -> None:
    tail_started = asyncio.Event()
    closed = False

    class Body(httpx.AsyncByteStream):
        async def __aiter__(self) -> AsyncIterator[bytes]:
            yield sse_reply([("response.created", {"type": "response.created"})]).body
            tail_started.set()
            await asyncio.Future[None]()

        async def aclose(self) -> None:
            nonlocal closed
            closed = True

    client = make_door_client(
        httpx.MockTransport(lambda request: httpx.Response(200, stream=Body()))
    )

    async def consume() -> None:
        async with client.stream(
            operation=DoorOperation.RESPONSES,
            payload=STREAM_PAYLOAD,
            caller=fixture_caller(),
            timeout_seconds=5,
        ) as stream:
            async for _ in stream.aiter_lines():
                if not read_all:
                    break

    task = asyncio.create_task(consume())
    await asyncio.wait_for(tail_started.wait(), timeout=1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert closed
