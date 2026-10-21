"""Caller identity and daily limits at HuleEdu's LLM provider door.

Purpose:
    Name who a paid AI call is made for and which daily limit refused it
    (ST-SKRIPT-41-01 B1, B4, B5). Every paid AI call carries one
    ``AiDoorCaller``; a door refusal for a pool, user share or USD ceiling
    becomes ``AiDailyLimitReached`` and ends the AI action's remaining calls.

Relationships:
    Built by the application handlers that run AI jobs from the job owner;
    sent by ``infrastructure.llm.door.client.HuleEduLlmDoorClient``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import has_at_least_role


@dataclass(frozen=True, slots=True)
class AiDoorCaller:
    """The teacher a paid AI call is made for, and the authority it carries.

    ``exempt`` users meet only the door's pools (B5). ``allow_paid_overage``
    is set only for the one AI action an admin approved past an exhausted pool.
    """

    user_id: UUID
    exempt: bool
    allow_paid_overage: bool


def door_caller_for(*, user: User, allow_paid_overage: bool) -> AiDoorCaller:
    """Build the door caller for ``user``; admins and superusers are exempt."""

    return AiDoorCaller(
        user_id=user.id,
        exempt=has_at_least_role(user=user, role=Role.ADMIN),
        allow_paid_overage=allow_paid_overage,
    )


class AiDailyLimit(StrEnum):
    """The door limit that refused a call (ST-HULE-14-03 D3-D5)."""

    POOL = "pool"
    USER_SHARE = "user_share"
    USD_CEILING = "usd_ceiling"


class AiDailyLimitReached(Exception):
    """The door refused a call for a daily limit; no provider call was made.

    Never retried: the AI action stops sending and records ``limit``.
    """

    def __init__(self, *, limit: AiDailyLimit) -> None:
        super().__init__(f"AI daily limit reached: {limit.value}")
        self.limit = limit
