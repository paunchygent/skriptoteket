"""Caller identity and daily limits at HuleEdu's LLM provider door.

Purpose:
    Name who a paid AI call is made for and which daily limit refused it
    (ST-SKRIPT-41-01 B1, B4, B5). Every paid AI call carries its action's
    ``AiDoorCaller``; a door refusal for a pool, user share or USD ceiling
    becomes ``AiDailyLimitReached``.

Relationships:
    Built by the application handlers that run AI jobs from the job owner;
    sent by ``infrastructure.llm.door.client.HuleEduLlmDoorClient``.
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import has_at_least_role


class AiDoorCaller:
    """The teacher one AI action's paid calls are made for, and their authority.

    Create one per AI action (a job or one synchronous request) and never share
    it: the action is admitted when its first door call succeeds, and every
    later call of the same action then runs as paid overage so a started job
    finishes (B4, C7) until its overage passes the per-job cap. ``exempt`` users
    meet only the door's pools (B5). ``overage_approved`` is set only by
    agent-run tooling after the user's yes (C6); such a run has no per-job cap.
    """

    __slots__ = ("_admitted", "_overage_usd_micros", "exempt", "overage_approved", "user_id")

    def __init__(self, *, user_id: UUID, exempt: bool, overage_approved: bool) -> None:
        self.user_id = user_id
        self.exempt = exempt
        self.overage_approved = overage_approved
        self._admitted = False
        self._overage_usd_micros = 0

    @property
    def admitted(self) -> bool:
        return self._admitted

    @property
    def allow_paid_overage(self) -> bool:
        return self.overage_approved or self._admitted

    @property
    def overage_usd_micros(self) -> int:
        """USD micros the door charged this action as paid overage so far."""

        return self._overage_usd_micros

    def admit(self) -> None:
        """Record that the action's first door call succeeded."""

        self._admitted = True

    def require_within_overage_cap(self, *, cap_usd_micros: int) -> None:
        """Refuse a further call once this action's overage passed the cap (C7)."""

        if not self.overage_approved and self._overage_usd_micros > cap_usd_micros:
            raise AiJobOverageCapReached(
                overage_usd_micros=self._overage_usd_micros, cap_usd_micros=cap_usd_micros
            )

    def charge_overage(self, usd_micros: int) -> None:
        if usd_micros < 0:
            raise ValueError("A door overage charge cannot be negative.")
        self._overage_usd_micros += usd_micros


def door_caller_for(*, user: User, overage_approved: bool = False) -> AiDoorCaller:
    """Start the door caller of one AI action for ``user``; admins are exempt."""

    return AiDoorCaller(
        user_id=user.id,
        exempt=has_at_least_role(user=user, role=Role.ADMIN),
        overage_approved=overage_approved,
    )


class AiDailyLimit(StrEnum):
    """The door limit that refused a call (ST-HULE-14-03 D3-D5)."""

    POOL = "pool"
    USER_SHARE = "user_share"
    USD_CEILING = "usd_ceiling"


class AiDailyLimitReached(Exception):
    """The door refused a call for a daily limit; no provider call was made.

    Never retried; the AI action records ``limit`` and shows the limit note.
    """

    def __init__(self, *, limit: AiDailyLimit) -> None:
        super().__init__(f"AI daily limit reached: {limit.value}")
        self.limit = limit


class AiJobOverageCapReached(Exception):
    """A started action's paid overage passed the per-job cap (C7); stop the job."""

    def __init__(self, *, overage_usd_micros: int, cap_usd_micros: int) -> None:
        super().__init__(
            f"AI job overage {overage_usd_micros} USD micros passed the cap {cap_usd_micros}"
        )
        self.overage_usd_micros = overage_usd_micros
        self.cap_usd_micros = cap_usd_micros
