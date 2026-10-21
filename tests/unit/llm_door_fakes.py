"""Fake LLM provider door for unit tests and deterministic replays.

``RecordingDoor`` implements ``LlmDoorClientProtocol``: it records each
operation, payload and caller and answers from a responder, so replays serve
recorded OpenAI bodies at the door seam and never reach the door (B6).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from pydantic import JsonValue

from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.domain.llm_door import AiDailyLimit, AiDailyLimitReached, AiDoorCaller
from skriptoteket.protocols.llm_door import DoorOperation, DoorReply, LlmDoorClientProtocol

FIXTURE_CALLER = AiDoorCaller(
    user_id=UUID("00000000-0000-0000-0000-00000000a11e"),
    exempt=True,
    allow_paid_overage=False,
)


@dataclass(frozen=True, slots=True)
class DoorSent:
    operation: DoorOperation
    payload: dict[str, JsonValue]
    caller: AiDoorCaller
    timeout_seconds: float


DoorResponder = Callable[[DoorSent], DoorReply]


def json_reply(body: JsonValue, *, status_code: int = 200) -> DoorReply:
    return DoorReply(
        status_code=status_code,
        headers={"content-type": "application/json"},
        body=json.dumps(body).encode(),
    )


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
    def __init__(self, responder: DoorResponder) -> None:
        self.sent: list[DoorSent] = []
        self._responder = responder

    async def send(
        self,
        *,
        operation: DoorOperation,
        payload: Mapping[str, JsonValue],
        caller: AiDoorCaller,
        timeout_seconds: float,
    ) -> DoorReply:
        sent = DoorSent(
            operation=operation,
            payload=dict(payload),
            caller=caller,
            timeout_seconds=timeout_seconds,
        )
        self.sent.append(sent)
        return self._responder(sent)


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
