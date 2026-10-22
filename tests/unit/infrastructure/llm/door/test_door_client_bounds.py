"""The door client bounds its fan-out, retries capacity 429s and ends local exhaustion as busy."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import replace
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from pydantic import JsonValue

from skriptoteket.config import Settings
from skriptoteket.domain.llm_door import (
    AiDailyLimitReached,
    AiDoorBusy,
    AiDoorCaller,
    AiJobOverageCapReached,
    AiOverageAuthority,
)
from skriptoteket.infrastructure.llm.door.client import DoorBounds, HuleEduLlmDoorClient
from skriptoteket.protocols.llm_door import DoorOperation, DoorReply

PAYLOAD: dict[str, JsonValue] = {"model": "gpt-6-luna", "input": "hej"}
CAPACITY_BODY = {"error": {"type": "huleedu_openai_door", "code": "openai_door_admission_full"}}
LIMIT_BODY = {
    "error": {
        "code": "openai_caller_user_share_exceeded",
        "limit": "user_share",
    }
}


class RecordingSleeper:
    def __init__(self) -> None:
        self.delays: list[float] = []
        self.on_sleep: Callable[[], Awaitable[None]] | None = None

    async def sleep(self, seconds: float) -> None:
        self.delays.append(seconds)
        if self.on_sleep is not None:
            await self.on_sleep()


class Gate:
    """A transport that holds every request open and records how many run at once."""

    def __init__(self) -> None:
        self.release = asyncio.Event()
        self.active = 0
        self.peak = 0
        self.started = 0

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        self.started += 1
        self.active += 1
        self.peak = max(self.peak, self.active)
        try:
            await self.release.wait()
        finally:
            self.active -= 1
        return httpx.Response(200, json={})


def _client(
    handler: Callable[[httpx.Request], httpx.Response]
    | Callable[[httpx.Request], Coroutine[None, None, httpx.Response]],
    *,
    sleeper: RecordingSleeper | None = None,
    **bounds: Any,
) -> HuleEduLlmDoorClient:
    return HuleEduLlmDoorClient(
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        base_url="http://door.test:8080",
        internal_api_key="internal-key",
        job_overage_cap_usd_micros=1_000_000,
        sleeper=sleeper or RecordingSleeper(),
        bounds=replace(DoorBounds.from_settings(Settings()), **bounds),
    )


def _caller(user_id: UUID | None = None) -> AiDoorCaller:
    return AiDoorCaller(
        user_id=user_id or uuid4(), exempt=True, authority=AiOverageAuthority.JOB_CONTINUATION
    )


async def _send(client: HuleEduLlmDoorClient, caller: AiDoorCaller) -> DoorReply:
    return await client.send(
        operation=DoorOperation.RESPONSES, payload=PAYLOAD, caller=caller, timeout_seconds=5
    )


async def _settle() -> None:
    for _ in range(100):
        await asyncio.sleep(0)


def _capacity(retry_after: str | None) -> httpx.Response:
    headers = {} if retry_after is None else {"Retry-After": retry_after}
    return httpx.Response(429, headers=headers, json=CAPACITY_BODY)


async def test_one_action_never_has_more_calls_in_flight_than_its_fan_out_bound() -> None:
    gate = Gate()
    client = _client(gate, max_in_flight=100, per_action_max_in_flight=4)
    caller = _caller()

    tasks = [asyncio.create_task(_send(client, caller)) for _ in range(50)]
    await _settle()
    assert (gate.active, gate.peak) == (4, 4)

    gate.release.set()
    replies = await asyncio.gather(*tasks)

    assert gate.peak == 4
    assert gate.started == 50
    assert all(reply.is_success for reply in replies)


async def test_each_action_gets_its_own_fan_out_bound() -> None:
    gate = Gate()
    client = _client(gate, max_in_flight=100, per_action_max_in_flight=4)
    first, second = _caller(), _caller()

    tasks = [asyncio.create_task(_send(client, caller)) for caller in (first, second)]
    tasks += [asyncio.create_task(_send(client, first)) for _ in range(20)]
    tasks += [asyncio.create_task(_send(client, second)) for _ in range(20)]
    await _settle()
    assert (gate.active, gate.peak) == (8, 8)

    gate.release.set()
    await asyncio.gather(*tasks)
    assert gate.peak == 8


async def test_the_process_bound_holds_across_actions_and_a_waiting_call_ends_as_busy() -> None:
    gate = Gate()
    client = _client(gate, max_in_flight=3, per_action_max_in_flight=8, slot_wait_seconds=0.05)

    holders = [asyncio.create_task(_send(client, _caller())) for _ in range(3)]
    await _settle()
    assert gate.active == 3

    with pytest.raises(AiDoorBusy) as raised:
        await _send(client, _caller())
    assert raised.value.retry_after_seconds is None
    assert gate.peak == 3

    gate.release.set()
    await asyncio.gather(*holders)
    assert (await _send(client, _caller())).is_success


async def test_a_call_that_waits_for_a_process_slot_runs_once_one_frees() -> None:
    gate = Gate()
    client = _client(gate, max_in_flight=2, per_action_max_in_flight=8, slot_wait_seconds=5)

    tasks = [asyncio.create_task(_send(client, _caller())) for _ in range(6)]
    await _settle()
    assert gate.peak == 2

    gate.release.set()
    replies = await asyncio.gather(*tasks)
    assert (gate.peak, gate.started, len(replies)) == (2, 6, 6)


async def test_a_busy_wait_releases_the_action_slot_it_held() -> None:
    gate = Gate()
    client = _client(gate, max_in_flight=1, per_action_max_in_flight=1, slot_wait_seconds=0.02)
    holder = asyncio.create_task(_send(client, _caller()))
    await _settle()
    waiting = _caller()

    for _ in range(2):
        with pytest.raises(AiDoorBusy):
            await _send(client, waiting)

    gate.release.set()
    await holder
    assert (await _send(client, waiting)).is_success


@pytest.mark.parametrize(
    ("header", "waited"),
    [("7", 7.0), ("120", 10.0), (None, 2.0), ("soon", 2.0), ("Wed, 21 Oct 2026 07:28:00 GMT", 2.0)],
)
async def test_a_capacity_429_is_resent_after_its_capped_retry_after(
    header: str | None, waited: float
) -> None:
    replies = iter([_capacity(header), httpx.Response(200, json={"id": "ok"})])
    sleeper = RecordingSleeper()
    client = _client(
        lambda request: next(replies),
        sleeper=sleeper,
        capacity_retries=2,
        retry_after_max_seconds=10,
        retry_after_fallback_seconds=2,
    )
    caller = _caller()

    reply = await _send(client, caller)

    assert sleeper.delays == [waited]
    assert (reply.status_code, caller.admitted) == (200, True)


async def test_a_door_still_full_after_the_retries_ends_as_busy_with_its_last_retry_after() -> None:
    retry_afters = iter(["3", "5", "9", "11"])
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _capacity(next(retry_afters))

    sleeper = RecordingSleeper()
    client = _client(handle, sleeper=sleeper, capacity_retries=2, retry_after_max_seconds=10)

    with pytest.raises(AiDoorBusy) as raised:
        await _send(client, _caller())

    assert len(requests) == 3
    assert sleeper.delays == [3.0, 5.0]
    assert raised.value.retry_after_seconds == 9


async def test_a_door_that_never_names_a_retry_after_ends_as_busy_without_one() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _capacity(None)

    client = _client(handle, capacity_retries=0)

    with pytest.raises(AiDoorBusy) as raised:
        await _send(client, _caller())

    assert len(requests) == 1
    assert raised.value.retry_after_seconds is None


async def test_no_slot_is_held_while_a_call_sleeps_on_retry_after() -> None:
    first_user, second_user = uuid4(), uuid4()
    first_attempts = 0

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal first_attempts
        if request.headers["X-HuleEdu-User-ID"] == str(first_user):
            first_attempts += 1
            return _capacity("4") if first_attempts == 1 else httpx.Response(200, json={})
        return httpx.Response(200, json={"second": True})

    wake = asyncio.Event()
    sleeper = RecordingSleeper()

    async def wait_for_wake() -> None:
        await wake.wait()

    sleeper.on_sleep = wait_for_wake
    client = _client(handle, sleeper=sleeper, max_in_flight=1, per_action_max_in_flight=1)
    first = asyncio.create_task(_send(client, _caller(first_user)))
    await _settle()
    assert sleeper.delays == [4.0]
    assert not first.done()

    second = await asyncio.wait_for(_send(client, _caller(second_user)), timeout=1)
    assert second.is_success
    same_action_probe = asyncio.create_task(_send(client, _caller(first_user)))
    assert (await asyncio.wait_for(same_action_probe, timeout=1)).is_success

    wake.set()
    assert (await first).is_success
    assert first_attempts == 3


async def test_the_overage_cap_is_checked_again_before_each_resend() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _capacity("1")

    caller = _caller()
    sleeper = RecordingSleeper()

    async def overspend() -> None:
        caller.charge_overage(2_000_000)

    sleeper.on_sleep = overspend
    client = _client(handle, sleeper=sleeper, capacity_retries=2)

    with pytest.raises(AiJobOverageCapReached):
        await _send(client, caller)

    assert len(requests) == 1


async def test_a_limit_429_raises_without_any_retry() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(429, headers={"Retry-After": "5"}, json=LIMIT_BODY)

    sleeper = RecordingSleeper()
    client = _client(handle, sleeper=sleeper, capacity_retries=2)

    with pytest.raises(AiDailyLimitReached):
        await _send(client, _caller())

    assert len(requests) == 1
    assert sleeper.delays == []


async def test_a_limit_429_after_a_capacity_429_still_raises_the_limit() -> None:
    replies = iter([_capacity("1"), httpx.Response(429, json=LIMIT_BODY)])
    client = _client(lambda request: next(replies), capacity_retries=2)

    with pytest.raises(AiDailyLimitReached):
        await _send(client, _caller())


async def test_an_exhausted_connection_pool_is_busy_not_a_door_timeout() -> None:
    def pool_exhausted(request: httpx.Request) -> httpx.Response:
        raise httpx.PoolTimeout("no free connection", request=request)

    with pytest.raises(AiDoorBusy) as raised:
        await _send(_client(pool_exhausted), _caller())

    assert raised.value.retry_after_seconds is None


async def test_the_pool_wait_is_bounded_separately_from_the_call_timeout() -> None:
    seen: list[dict[str, float | None]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request.extensions["timeout"])
        return httpx.Response(200, json={})

    await _send(_client(handle, pool_timeout_seconds=1.5), _caller())

    assert seen == [{"connect": 5, "read": 5, "write": 5, "pool": 1.5}]


@pytest.mark.parametrize(
    "bounds",
    [
        {"max_in_flight": 0},
        {"per_action_max_in_flight": 0},
        {"capacity_retries": -1},
        {"slot_wait_seconds": 0},
        {"pool_timeout_seconds": 0},
        {"retry_after_max_seconds": 0},
        {"retry_after_fallback_seconds": 0},
    ],
)
def test_nonsense_bounds_are_refused(bounds: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        replace(DoorBounds.from_settings(Settings()), **bounds)
