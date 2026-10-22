"""Fake LLM provider door for unit tests and deterministic replays.

``RecordingDoor`` implements ``LlmDoorClientProtocol``: it records each
operation, payload, caller and the paid-overage mode sent, answers from a
responder, and settles each answer on the caller exactly as the real client
does (admission, overage charge, per-job cap after each charge),
so replays serve recorded OpenAI bodies at the door seam and never reach the
door (B6). ``stream`` serves the same replies as an open ``DoorStream``,
consuming private settled-charge events and admitting the caller on a success
as the real client does. Normal exit drains settlement; exceptional exit closes.
"""

from __future__ import annotations

import inspect
import json
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from pydantic import JsonValue

from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.domain.llm_door import (
    AiDailyLimit,
    AiDailyLimitReached,
    AiDoorCaller,
    AiOverageAuthority,
)
from skriptoteket.infrastructure.llm.door.client import record_door_charge, settle_door_reply
from skriptoteket.infrastructure.llm.door.stream import ChargeRecordingDoorStream
from skriptoteket.protocols.llm_door import DoorOperation, DoorReply, LlmDoorClientProtocol

FIXTURE_USER_ID = UUID("00000000-0000-0000-0000-00000000a11e")


def fixture_caller(
    *,
    exempt: bool = True,
    authority: AiOverageAuthority = AiOverageAuthority.JOB_CONTINUATION,
) -> AiDoorCaller:
    """A fresh caller for one AI action (callers carry per-action admission)."""

    return AiDoorCaller(user_id=FIXTURE_USER_ID, exempt=exempt, authority=authority)


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


def sse_reply(events: Iterable[tuple[str, JsonValue]], *, status_code: int = 200) -> DoorReply:
    """A streamed Responses answer: one ``event:``/``data:`` pair per event."""

    body = "".join(f"event: {event}\ndata: {json.dumps(data)}\n\n" for event, data in events)
    return DoorReply(
        status_code=status_code,
        headers={"content-type": "text/event-stream"},
        body=body.encode(),
    )


@dataclass(frozen=True, slots=True)
class FakeDoorStream:
    status_code: int
    headers: Mapping[str, str]
    body: bytes

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    async def aiter_lines(self) -> AsyncIterator[str]:
        if not self.is_success:
            return
        for line in self.body.decode().splitlines():
            yield line


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
        settle_door_reply(caller, reply, cap_usd_micros=self._cap_usd_micros)
        return reply

    @asynccontextmanager
    async def stream(
        self,
        *,
        operation: DoorOperation,
        payload: Mapping[str, JsonValue],
        caller: AiDoorCaller,
        timeout_seconds: float,
    ) -> AsyncIterator[FakeDoorStream | ChargeRecordingDoorStream]:
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
        raw_stream = FakeDoorStream(
            status_code=reply.status_code, headers=reply.headers, body=reply.body
        )
        if not reply.is_success:
            yield raw_stream
            return
        caller.admit()

        def record_charge(headers: Mapping[str, str]) -> None:
            record_door_charge(caller, headers)
            caller.require_within_overage_cap(cap_usd_micros=self._cap_usd_micros)

        stream = ChargeRecordingDoorStream(stream=raw_stream, record_charge=record_charge)
        try:
            yield stream
        except BaseException:
            await stream.finish(drain=False)
            raise
        else:
            await stream.finish()


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
