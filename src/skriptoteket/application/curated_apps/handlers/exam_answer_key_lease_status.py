"""Operator query for the answer-key daily token-lease balance.

Purpose:
    Let operators read the current UTC day's lease balance (allocated,
    charged, remaining) so exhaustion fail-closes are observable without any
    teacher-facing surface.

Relationships:
    Served through the admin API route in
    ``web.api.v1.admin_answer_key_lease``; reads the lease ledger owned by
    ``infrastructure.repositories.exam_answer_key_token_leases``.
"""

from __future__ import annotations

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    AnswerKeyTokenLeaseDayUsage,
    lease_utc_day,
)
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import (
    AnswerKeyLeaseStatusHandlerProtocol,
    AnswerKeyTokenLeaseRepositoryProtocol,
)


class GetAnswerKeyLeaseStatusHandler(AnswerKeyLeaseStatusHandlerProtocol):
    """Read the current UTC day's lease balance for an operator."""

    def __init__(
        self,
        *,
        leases: AnswerKeyTokenLeaseRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._leases = leases
        self._clock = clock

    async def handle(self, *, actor: User) -> AnswerKeyTokenLeaseDayUsage:
        require_at_least_role(user=actor, role=Role.ADMIN)
        return await self._leases.day_usage(utc_day=lease_utc_day(self._clock.now()))
