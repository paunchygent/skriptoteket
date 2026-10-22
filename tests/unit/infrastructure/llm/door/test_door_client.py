"""The door client forwards the body with the caller's headers and types its failures."""

from __future__ import annotations

import json

import httpx
import pytest

from skriptoteket.domain.llm_door import (
    AiDailyLimit,
    AiDailyLimitReached,
    AiDoorBusy,
    AiDoorCaller,
    AiOverageAuthority,
)
from skriptoteket.protocols.llm_door import DoorOperation, DoorRequestFailed, DoorTimeout
from tests.unit.infrastructure.llm.door.door_client_support import (
    PAYLOAD,
    TEACHER,
    make_door_client,
    refusal_response,
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
    reply = await make_door_client(httpx.MockTransport(handle)).send(
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


@pytest.mark.parametrize(
    ("code", "limit"),
    [
        ("openai_complimentary_allowance_exceeded", AiDailyLimit.POOL),
        ("openai_caller_user_share_exceeded", AiDailyLimit.USER_SHARE),
        ("openai_caller_usd_ceiling_exceeded", AiDailyLimit.USD_CEILING),
    ],
)
async def test_a_limit_429_raises_the_named_limit(code: str, limit: AiDailyLimit) -> None:
    client = make_door_client(
        httpx.MockTransport(lambda request: refusal_response(code, limit.value))
    )

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
        refusal_response("openai_door_admission_full"),
        refusal_response("openai_complimentary_allowance_exceeded", None),
        refusal_response("openai_complimentary_allowance_exceeded", "weekly"),
        httpx.Response(429, text="not json"),
        httpx.Response(429, json={"error": "rate limited"}),
    ],
)
async def test_a_429_that_names_no_limit_is_a_capacity_refusal_never_a_reply(
    response: httpx.Response,
) -> None:
    client = make_door_client(httpx.MockTransport(lambda request: response))

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
        await make_door_client(httpx.MockTransport(timeout)).send(
            operation=DoorOperation.RESPONSES, payload=PAYLOAD, caller=caller, timeout_seconds=5
        )
    with pytest.raises(DoorRequestFailed):
        await make_door_client(httpx.MockTransport(refused)).send(
            operation=DoorOperation.RESPONSES, payload=PAYLOAD, caller=caller, timeout_seconds=5
        )
