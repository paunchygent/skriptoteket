"""Fake LLM provider door for unit tests and deterministic replays.

``RecordingDoor`` implements ``LlmDoorClientProtocol``: it records each
operation, payload, caller and the paid-overage mode sent, answers from a
responder, and admits the caller, counts its overage charge and enforces the
per-job cap as the real client does,
so replays serve recorded OpenAI bodies at the door seam and never reach the
door (B6).
"""

from __future__ import annotations

import inspect
import json
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from pydantic import JsonValue

from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.domain.llm_door import AiDailyLimit, AiDailyLimitReached, AiDoorCaller
from skriptoteket.infrastructure.llm.door.client import record_door_charge
from skriptoteket.protocols.llm_door import DoorOperation, DoorReply, LlmDoorClientProtocol

FIXTURE_USER_ID = UUID("00000000-0000-0000-0000-00000000a11e")


def fixture_caller(*, exempt: bool = True, overage_approved: bool = False) -> AiDoorCaller:
    """A fresh caller for one AI action (callers carry per-action admission)."""

    return AiDoorCaller(user_id=FIXTURE_USER_ID, exempt=exempt, overage_approved=overage_approved)


@dataclass(frozen=True, slots=True)
class DoorSent:
    operation: DoorOperation
    payload: dict[str, JsonValue]
    caller: AiDoorCaller
    timeout_seconds: float
    allow_paid_overage: bool


DoorResponder = Callable[[DoorSent], DoorReply | Awaitable[DoorReply]]


def json_reply(
    body: JsonValue, *, status_code: int = 200, overage_usd_micros: int | None = None
) -> DoorReply:
    """A door reply; ``overage_usd_micros`` marks it as a paid-overage charge."""

    headers = {
        "content-type": "application/json",
        "X-HuleEdu-Charge-Kind": "complimentary",
        "X-HuleEdu-Charge-USD-Micros": "0",
    }
    if overage_usd_micros is not None:
        headers["X-HuleEdu-Charge-Kind"] = "overage"
        headers["X-HuleEdu-Charge-USD-Micros"] = str(overage_usd_micros)
    return DoorReply(status_code=status_code, headers=headers, body=json.dumps(body).encode())


def replies_in_order(bodies: Iterable[JsonValue]) -> DoorResponder:
    """Serve ``bodies`` one per call, failing loudly past the last one."""

    remaining = iter(list(bodies))

    def respond(sent: DoorSent) -> DoorReply:
        body = next(remaining, None)
        if body is None:
            raise AssertionError(f"no recorded door reply left for {sent.operation.value}")
        return json_reply(body)

    return respond


def limit_refusal(limit: AiDailyLimit) -> DoorResponder:
    """Refuse every call for ``limit`` as the door client raises it."""

    def respond(sent: DoorSent) -> DoorReply:
        raise AiDailyLimitReached(limit=limit)

    return respond


class RecordingDoor(LlmDoorClientProtocol):
    def __init__(self, responder: DoorResponder, *, cap_usd_micros: int = 1_000_000) -> None:
        self.sent: list[DoorSent] = []
        self._responder = responder
        self._cap_usd_micros = cap_usd_micros

    async def send(
        self,
        *,
        operation: DoorOperation,
        payload: Mapping[str, JsonValue],
        caller: AiDoorCaller,
        timeout_seconds: float,
    ) -> DoorReply:
        caller.require_within_overage_cap(cap_usd_micros=self._cap_usd_micros)
        sent = DoorSent(
            operation=operation,
            payload=dict(payload),
            caller=caller,
            timeout_seconds=timeout_seconds,
            allow_paid_overage=caller.allow_paid_overage,
        )
        self.sent.append(sent)
        reply = self._responder(sent)
        if inspect.isawaitable(reply):
            reply = await reply
        if reply.is_success:
            caller.admit()
        record_door_charge(caller, reply.headers)
        return reply


def user_with_role(role: Role, *, user_id: UUID) -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=user_id,
        email=f"{role.value}@example.com",
        role=role,
        auth_provider=AuthProvider.LOCAL,
        email_verified=True,
        created_at=now,
        updated_at=now,
    )
