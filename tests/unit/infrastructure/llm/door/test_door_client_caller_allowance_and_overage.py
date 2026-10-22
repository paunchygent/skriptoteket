"""The door client sends the caller's allowance mode and enforces the per-job overage cap."""

from __future__ import annotations

import httpx
import pytest

from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.llm_door import (
    AiDailyLimit,
    AiDailyLimitReached,
    AiDoorCaller,
    AiJobOverageCapReached,
    AiOverageAuthority,
    ai_limit_note,
    door_caller_for,
    tooling_caller,
)
from skriptoteket.infrastructure.llm.door import client as door_client
from skriptoteket.protocols.llm_door import DoorOperation
from tests.unit.infrastructure.llm.door.door_client_support import (
    PAYLOAD,
    TEACHER,
    make_door_client,
    refusal_response,
)
from tests.unit.llm_door_fakes import user_with_role


def _charged(kind: str, micros: int) -> httpx.Response:
    return httpx.Response(
        200,
        headers={"X-HuleEdu-Charge-Kind": kind, "X-HuleEdu-Charge-USD-Micros": str(micros)},
        json={},
    )


async def test_a_non_exempt_caller_omits_the_exempt_header_and_overage_sets_the_mode() -> None:
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={})

    caller = AiDoorCaller(user_id=TEACHER, exempt=False, authority=AiOverageAuthority.APPROVED_RUN)
    await make_door_client(httpx.MockTransport(handle)).send(
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

    client = make_door_client(httpx.MockTransport(handle))
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

    client = make_door_client(httpx.MockTransport(handle))
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

    client = make_door_client(httpx.MockTransport(handle))
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
    client = make_door_client(httpx.MockTransport(lambda request: _charged("overage", 2_000_000)))
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
    client = make_door_client(
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
        return refusal_response("openai_complimentary_allowance_exceeded", "pool")

    client = make_door_client(httpx.MockTransport(handle))
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

    client = make_door_client(httpx.MockTransport(handle))
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
