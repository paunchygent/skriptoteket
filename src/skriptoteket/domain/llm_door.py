"""Caller identity and daily limits at HuleEdu's LLM provider door.

Purpose:
    Name who a paid AI call is made for, when it may cross the free pool,
    and which daily limit refused it (ST-SKRIPT-41-01 B1, B4, B5). Every paid
    AI call carries its action's ``AiDoorCaller``; a door refusal for a pool,
    user share or USD ceiling becomes ``AiDailyLimitReached``, whose teacher
    note ``ai_limit_note`` picks from the limit; a door with no room for the
    call becomes ``AiDoorBusy`` with the try-again note (B7).

Relationships:
    Built by the application handlers that run AI jobs from the job owner and
    by agent-run tooling; sent by
    ``infrastructure.llm.door.client.HuleEduLlmDoorClient``.
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import has_at_least_role


class AiOverageAuthority(StrEnum):
    """When an AI action's calls may cross the free pool into paid overage.

    ``JOB_CONTINUATION``: an app job. It is admitted when its first door call
    succeeds; every later call runs as paid overage so a started job finishes
    (C7), up to the per-job cap. ``APPROVED_RUN``: one agent-tooling invocation
    the user approved paid overage for (C6); every call may cross the pool and
    no per-job cap applies. ``FREE_ONLY``: agent tooling without that approval;
    no call ever crosses the pool, so pool exhaustion stops the run.
    """

    JOB_CONTINUATION = "job_continuation"
    APPROVED_RUN = "approved_run"
    FREE_ONLY = "free_only"


class AiDoorCaller:
    """The teacher one AI action's paid calls are made for, and their authority.

    Create one per AI action (a job, one synchronous request, or one tooling
    invocation) and never share it across actions. ``exempt`` users meet only
    the door's pools (B5).
    """

    __slots__ = ("_admitted", "_overage_usd_micros", "authority", "exempt", "user_id")

    def __init__(self, *, user_id: UUID, exempt: bool, authority: AiOverageAuthority) -> None:
        self.user_id = user_id
        self.exempt = exempt
        self.authority = authority
        self._admitted = False
        self._overage_usd_micros = 0

    @property
    def admitted(self) -> bool:
        return self._admitted

    @property
    def allow_paid_overage(self) -> bool:
        match self.authority:
            case AiOverageAuthority.APPROVED_RUN:
                return True
            case AiOverageAuthority.JOB_CONTINUATION:
                return self._admitted
            case AiOverageAuthority.FREE_ONLY:
                return False

    @property
    def overage_usd_micros(self) -> int:
        """USD micros the door charged this action as paid overage so far."""

        return self._overage_usd_micros

    def admit(self) -> None:
        """Record that the action's first door call succeeded."""

        self._admitted = True

    def require_within_overage_cap(self, *, cap_usd_micros: int) -> None:
        """Stop an app job whose paid overage passed the per-job cap (C7).

        Checked before each call and again after each charge is recorded, so
        the call that crosses the cap stops the job even when no call follows.
        """

        if (
            self.authority is AiOverageAuthority.JOB_CONTINUATION
            and self._overage_usd_micros > cap_usd_micros
        ):
            raise AiJobOverageCapReached(
                overage_usd_micros=self._overage_usd_micros, cap_usd_micros=cap_usd_micros
            )

    def charge_overage(self, usd_micros: int) -> None:
        if usd_micros < 0:
            raise ValueError("A door overage charge cannot be negative.")
        self._overage_usd_micros += usd_micros


def door_caller_for(*, user: User) -> AiDoorCaller:
    """Start the door caller of one app AI job for ``user``; admins are exempt."""

    return AiDoorCaller(
        user_id=user.id,
        exempt=has_at_least_role(user=user, role=Role.ADMIN),
        authority=AiOverageAuthority.JOB_CONTINUATION,
    )


def tooling_caller(*, user_id: UUID, paid_overage_approved: bool) -> AiDoorCaller:
    """Start the door caller of one agent-tooling invocation (C6).

    ``paid_overage_approved`` comes from the invocation's explicit flag, set
    only after the user's yes; it covers that invocation and nothing after it.
    """

    return AiDoorCaller(
        user_id=user_id,
        exempt=True,
        authority=(
            AiOverageAuthority.APPROVED_RUN
            if paid_overage_approved
            else AiOverageAuthority.FREE_ONLY
        ),
    )


class AiDailyLimit(StrEnum):
    """The door limit that refused a call (ST-HULE-14-03 D3-D5)."""

    POOL = "pool"
    USER_SHARE = "user_share"
    USD_CEILING = "usd_ceiling"


_USER_SHARE_NOTE = "Du har nått din gräns för AI-hjälp i dag. Försök igen i morgon."
_APP_LIMIT_NOTE = "Appens AI-hjälp har nått dagens gräns. Försök igen i morgon."


def ai_limit_note(limit: AiDailyLimit) -> str:
    """The teacher note for a door limit (B4): the user's own share, or the app's."""

    if limit is AiDailyLimit.USER_SHARE:
        return _USER_SHARE_NOTE
    return _APP_LIMIT_NOTE


class AiDailyLimitReached(Exception):
    """The door refused a call for a daily limit; no provider call was made.

    Never retried; the AI action records ``limit`` and shows its note.
    """

    def __init__(self, *, limit: AiDailyLimit) -> None:
        super().__init__(f"AI daily limit reached: {limit.value}")
        self.limit = limit


class AiJobOverageCapReached(Exception):
    """A started app job's paid overage passed the per-job cap (C7); stop the job.

    The job records ``AiDailyLimit.POOL`` and shows the app limit note.
    """

    def __init__(self, *, overage_usd_micros: int, cap_usd_micros: int) -> None:
        super().__init__(
            f"AI job overage {overage_usd_micros} USD micros passed the cap {cap_usd_micros}"
        )
        self.overage_usd_micros = overage_usd_micros
        self.cap_usd_micros = cap_usd_micros


_TRY_AGAIN_NOTE = "AI-hjälpen har många förfrågningar just nu. Försök igen om en stund."


class AiDoorBusy(Exception):
    """The door, or this process's share of it, had no room for a call (B7).

    Raised after the door client's bounded Retry-After retries; the AI action
    stops and shows ``ai_try_again_note``. ``retry_after_seconds`` is the
    door's last Retry-After, or None when the door named none.
    """

    def __init__(self, *, retry_after_seconds: int | None) -> None:
        super().__init__(f"AI door busy; retry after {retry_after_seconds} seconds")
        self.retry_after_seconds = retry_after_seconds


def ai_try_again_note() -> str:
    """The teacher note for a busy door: try again in a moment."""

    return _TRY_AGAIN_NOTE
