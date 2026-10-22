"""The door client sends the caller's identity and turns limit 429s into a typed stop."""

from __future__ import annotations

import json
from uuid import UUID

import httpx
import pytest
from pydantic import JsonValue

from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.llm_door import (
    AiDailyLimit,
    AiDailyLimitReached,
    AiDoorBusy,
    AiDoorCaller,
    AiJobOverageCapReached,
    AiOverageAuthority,
    ai_limit_note,
    door_caller_for,
    tooling_caller,
)
from skriptoteket.infrastructure.llm.door import client as door_client
from skriptoteket.infrastructure.llm.door.client import DoorBounds, HuleEduLlmDoorClient
from skriptoteket.protocols.llm_door import DoorOperation, DoorRequestFailed, DoorTimeout
from tests.unit.llm_door_fakes import user_with_role

TEACHER = UUID("11111111-1111-1111-1111-111111111111")
PAYLOAD: dict[str, JsonValue] = {"model": "gpt-6-luna", "input": "hej", "max_output_tokens": 64}


class _InstantSleeper:
    async def sleep(self, seconds: float) -> None:
        del seconds


def _client(handler: httpx.MockTransport) -> HuleEduLlmDoorClient:
    return HuleEduLlmDoorClient(
        sleeper=_InstantSleeper(),
        client=httpx.AsyncClient(transport=handler),
        base_url="http://door.test:8080/",
        internal_api_key="internal-key",
        job_overage_cap_usd_micros=1_000_000,
        bounds=DoorBounds.from_settings(Settings()),
    )


def _refusal(code: str, limit: str | None = None) -> httpx.Response:
    return httpx.Response(
        429,
        headers={"Retry-After": "3600"},
        json={
            "error": {
                "type": "huleedu_openai_door",
                "code": code,
                "message": "refused",
                "limit": limit,
            }
        },
    )


@pytest.mark.parametrize("operation", list(DoorOperation))
async def test_send_forwards_the_body_unchanged_with_the_callers_door_headers(
    operation: DoorOperation,
) -> None:
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"id": "resp_1"})

    caller = AiDoorCaller(
        user_id=TEACHER, exempt=True, authority=AiOverageAuthority.JOB_CONTINUATION
    )
    reply = await _client(httpx.MockTransport(handle)).send(
        operation=operation, payload=PAYLOAD, caller=caller, timeout_seconds=12
    )

    request = seen[0]
    assert request.method == "POST"
    assert str(request.url) == f"http://door.test:8080/internal/v1/openai/{operation.value}"
    assert json.loads(request.content) == PAYLOAD
    assert request.headers["X-Internal-API-Key"] == "internal-key"
    assert request.headers["X-Service-ID"] == "skriptoteket"
    assert request.headers["X-HuleEdu-User-ID"] == str(TEACHER)
    assert request.headers["X-HuleEdu-Exempt-Test-User"] == "true"
    assert request.headers["X-HuleEdu-OpenAI-Allowance-Mode"] == "free_allowance_only"
    assert "Authorization" not in request.headers
    assert reply.status_code == 200
    assert json.loads(reply.body) == {"id": "resp_1"}


async def test_a_non_exempt_caller_omits_the_exempt_header_and_overage_sets_the_mode() -> None:
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={})

    caller = AiDoorCaller(user_id=TEACHER, exempt=False, authority=AiOverageAuthority.APPROVED_RUN)
    await _client(httpx.MockTransport(handle)).send(
        operation=DoorOperation.RESPONSES, payload=PAYLOAD, caller=caller, timeout_seconds=5
    )

    assert "X-HuleEdu-Exempt-Test-User" not in seen[0].headers
    assert seen[0].headers["X-HuleEdu-OpenAI-Allowance-Mode"] == "allow_paid_overage"


async def test_an_action_admitted_by_its_first_success_sends_later_calls_as_paid_overage() -> None:
    statuses = iter([502, 200, 200])
    modes: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        modes.append(request.headers["X-HuleEdu-OpenAI-Allowance-Mode"])
        return httpx.Response(next(statuses), json={})

    client = _client(httpx.MockTransport(handle))
    caller = AiDoorCaller(
        user_id=TEACHER, exempt=True, authority=AiOverageAuthority.JOB_CONTINUATION
    )
    for _ in range(3):
        await client.send(
            operation=DoorOperation.RESPONSES, payload=PAYLOAD, caller=caller, timeout_seconds=5
        )

    assert modes == ["free_allowance_only", "free_allowance_only", "allow_paid_overage"]
    other_action = AiDoorCaller(
        user_id=TEACHER, exempt=True, authority=AiOverageAuthority.JOB_CONTINUATION
    )
    assert other_action.allow_paid_overage is False


@pytest.mark.parametrize(
    ("code", "limit"),
    [
        ("openai_complimentary_allowance_exceeded", AiDailyLimit.POOL),
        ("openai_caller_user_share_exceeded", AiDailyLimit.USER_SHARE),
        ("openai_caller_usd_ceiling_exceeded", AiDailyLimit.USD_CEILING),
    ],
)
async def test_a_limit_429_raises_the_named_limit(code: str, limit: AiDailyLimit) -> None:
    client = _client(httpx.MockTransport(lambda request: _refusal(code, limit.value)))

    with pytest.raises(AiDailyLimitReached) as raised:
        await client.send(
            operation=DoorOperation.RESPONSES,
            payload=PAYLOAD,
            caller=AiDoorCaller(
                user_id=TEACHER, exempt=False, authority=AiOverageAuthority.JOB_CONTINUATION
            ),
            timeout_seconds=5,
        )

    assert raised.value.limit is limit


@pytest.mark.parametrize(
    "response",
    [
        _refusal("openai_door_admission_full"),
        _refusal("openai_complimentary_allowance_exceeded", None),
        _refusal("openai_complimentary_allowance_exceeded", "weekly"),
        httpx.Response(429, text="not json"),
        httpx.Response(429, json={"error": "rate limited"}),
    ],
)
async def test_a_429_that_names_no_limit_is_a_capacity_refusal_never_a_reply(
    response: httpx.Response,
) -> None:
    client = _client(httpx.MockTransport(lambda request: response))

    with pytest.raises(AiDoorBusy):
        await client.send(
            operation=DoorOperation.DECISIONS,
            payload=PAYLOAD,
            caller=AiDoorCaller(
                user_id=TEACHER, exempt=True, authority=AiOverageAuthority.JOB_CONTINUATION
            ),
            timeout_seconds=5,
        )


async def test_transport_failures_become_typed_door_errors() -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    def refused(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    caller = AiDoorCaller(
        user_id=TEACHER, exempt=True, authority=AiOverageAuthority.JOB_CONTINUATION
    )
    with pytest.raises(DoorTimeout):
        await _client(httpx.MockTransport(timeout)).send(
            operation=DoorOperation.RESPONSES, payload=PAYLOAD, caller=caller, timeout_seconds=5
        )
    with pytest.raises(DoorRequestFailed):
        await _client(httpx.MockTransport(refused)).send(
            operation=DoorOperation.RESPONSES, payload=PAYLOAD, caller=caller, timeout_seconds=5
        )


@pytest.mark.parametrize(
    ("role", "exempt"),
    [
        (Role.USER, False),
        (Role.CONTRIBUTOR, False),
        (Role.ADMIN, True),
        (Role.SUPERUSER, True),
    ],
)
def test_admins_and_superusers_are_sent_exempt(role: Role, exempt: bool) -> None:
    caller = door_caller_for(user=user_with_role(role, user_id=TEACHER))

    assert (caller.user_id, caller.exempt, caller.allow_paid_overage) == (TEACHER, exempt, False)


def _charged(kind: str, micros: int) -> httpx.Response:
    return httpx.Response(
        200,
        headers={"X-HuleEdu-Charge-Kind": kind, "X-HuleEdu-Charge-USD-Micros": str(micros)},
        json={},
    )


async def test_the_call_whose_charge_passes_the_cap_stops_the_job_and_nothing_more_is_sent() -> (
    None
):
    replies = iter(
        [_charged("complimentary", 900), _charged("overage", 600_000), _charged("overage", 400_001)]
    )
    sent: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return next(replies)

    client = _client(httpx.MockTransport(handle))
    caller = AiDoorCaller(
        user_id=TEACHER, exempt=True, authority=AiOverageAuthority.JOB_CONTINUATION
    )
    for _ in range(2):
        await client.send(
            operation=DoorOperation.RESPONSES, payload=PAYLOAD, caller=caller, timeout_seconds=5
        )

    with pytest.raises(AiJobOverageCapReached) as raised:
        await client.send(
            operation=DoorOperation.RESPONSES, payload=PAYLOAD, caller=caller, timeout_seconds=5
        )
    assert caller.overage_usd_micros == 1_000_001
    with pytest.raises(AiJobOverageCapReached):
        await client.send(
            operation=DoorOperation.RESPONSES, payload=PAYLOAD, caller=caller, timeout_seconds=5
        )

    assert len(sent) == 3
    assert raised.value.overage_usd_micros == 1_000_001
    assert raised.value.cap_usd_micros == 1_000_000


async def test_a_job_exactly_at_the_cap_succeeds_and_still_sends_its_next_call() -> None:
    sent: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return _charged("overage", 1_000_000 if len(sent) == 1 else 1)

    client = _client(httpx.MockTransport(handle))
    caller = AiDoorCaller(
        user_id=TEACHER, exempt=True, authority=AiOverageAuthority.JOB_CONTINUATION
    )
    reply = await client.send(
        operation=DoorOperation.RESPONSES, payload=PAYLOAD, caller=caller, timeout_seconds=5
    )
    assert reply.is_success

    with pytest.raises(AiJobOverageCapReached):
        await client.send(
            operation=DoorOperation.RESPONSES, payload=PAYLOAD, caller=caller, timeout_seconds=5
        )

    assert len(sent) == 2


async def test_an_agent_approved_run_has_no_per_job_cap() -> None:
    client = _client(httpx.MockTransport(lambda request: _charged("overage", 2_000_000)))
    caller = AiDoorCaller(user_id=TEACHER, exempt=True, authority=AiOverageAuthority.APPROVED_RUN)
    for _ in range(3):
        await client.send(
            operation=DoorOperation.RESPONSES, payload=PAYLOAD, caller=caller, timeout_seconds=5
        )

    assert caller.overage_usd_micros == 6_000_000


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-HuleEdu-Charge-Kind": "overage"},
        {"X-HuleEdu-Charge-Kind": "overage", "X-HuleEdu-Charge-USD-Micros": "x"},
    ],
)
async def test_missing_or_invalid_charge_headers_count_no_overage(headers: dict[str, str]) -> None:
    client = _client(
        httpx.MockTransport(lambda request: httpx.Response(200, headers=headers, json={}))
    )
    caller = AiDoorCaller(
        user_id=TEACHER, exempt=True, authority=AiOverageAuthority.JOB_CONTINUATION
    )

    await client.send(
        operation=DoorOperation.RESPONSES, payload=PAYLOAD, caller=caller, timeout_seconds=5
    )

    assert caller.overage_usd_micros == 0


@pytest.mark.parametrize(("exempt", "warned"), [(True, False), (False, True)])
def test_missing_charge_headers_are_logged_only_for_a_non_exempt_caller(
    monkeypatch: pytest.MonkeyPatch, exempt: bool, warned: bool
) -> None:
    events: list[str] = []

    class _Logger:
        def warning(self, event: str, **_: object) -> None:
            events.append(event)

    monkeypatch.setattr(door_client, "logger", _Logger())
    caller = AiDoorCaller(
        user_id=TEACHER, exempt=exempt, authority=AiOverageAuthority.JOB_CONTINUATION
    )

    door_client.record_door_charge(caller, {})

    assert (events == ["llm_door_charge_headers_missing"]) is warned
    assert caller.overage_usd_micros == 0


async def test_tooling_without_approval_never_crosses_the_pool_after_a_success() -> None:
    modes: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        modes.append(request.headers["X-HuleEdu-OpenAI-Allowance-Mode"])
        if len(modes) == 1:
            return httpx.Response(200, json={})
        return _refusal("openai_complimentary_allowance_exceeded", "pool")

    client = _client(httpx.MockTransport(handle))
    caller = tooling_caller(user_id=TEACHER, paid_overage_approved=False)
    await client.send(
        operation=DoorOperation.RESPONSES, payload=PAYLOAD, caller=caller, timeout_seconds=5
    )

    with pytest.raises(AiDailyLimitReached) as raised:
        await client.send(
            operation=DoorOperation.RESPONSES, payload=PAYLOAD, caller=caller, timeout_seconds=5
        )

    assert modes == ["free_allowance_only", "free_allowance_only"]
    assert raised.value.limit is AiDailyLimit.POOL


async def test_an_approved_tooling_run_sends_every_call_as_paid_overage_without_a_cap() -> None:
    modes: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        modes.append(request.headers["X-HuleEdu-OpenAI-Allowance-Mode"])
        return _charged("overage", 2_000_000)

    client = _client(httpx.MockTransport(handle))
    caller = tooling_caller(user_id=TEACHER, paid_overage_approved=True)
    for _ in range(2):
        await client.send(
            operation=DoorOperation.RESPONSES, payload=PAYLOAD, caller=caller, timeout_seconds=5
        )

    assert modes == ["allow_paid_overage", "allow_paid_overage"]
    assert (caller.exempt, caller.overage_usd_micros) == (True, 4_000_000)


@pytest.mark.parametrize(
    ("limit", "note"),
    [
        (
            AiDailyLimit.USER_SHARE,
            "Du har nått din gräns för AI-hjälp i dag. Försök igen i morgon.",
        ),
        (AiDailyLimit.POOL, "Appens AI-hjälp har nått dagens gräns. Försök igen i morgon."),
        (AiDailyLimit.USD_CEILING, "Appens AI-hjälp har nått dagens gräns. Försök igen i morgon."),
    ],
)
def test_the_limit_note_names_the_users_share_or_the_apps_limit(
    limit: AiDailyLimit, note: str
) -> None:
    assert ai_limit_note(limit) == note
