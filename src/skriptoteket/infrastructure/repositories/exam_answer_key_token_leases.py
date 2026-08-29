"""PostgreSQL repository for the answer-key daily token lease.

Purpose:
    Own the single Postgres lease table through the caller's Unit of Work:
    reserve before every provider call, never refund, and refuse with the
    typed UTC-reset refusal when the day's allowance is exhausted.

Relationships:
    Implements ``AnswerKeyTokenLeaseRepositoryProtocol``; concurrency safety
    comes from a per-UTC-day transaction-scoped advisory lock, so competing
    reservations serialize inside their owning transactions.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    AnswerKeyTokenLease,
    AnswerKeyTokenLeaseDayUsage,
    AnswerKeyTokenLeaseState,
    lease_utc_day,
    refuse_lease,
)
from skriptoteket.domain.errors import not_found
from skriptoteket.infrastructure.db.models.exam_answer_key_token_lease import (
    ExamAnswerKeyTokenLeaseModel,
)
from skriptoteket.protocols.exam_answer_key import AnswerKeyTokenLeaseRepositoryProtocol


class PostgreSQLAnswerKeyTokenLeaseRepository(AnswerKeyTokenLeaseRepositoryProtocol):
    """Postgres lease ledger on a request-scoped session; UoW owns commit."""

    def __init__(self, session: AsyncSession, *, daily_token_limit: int) -> None:
        if daily_token_limit <= 0:
            raise ValueError("daily_token_limit must be positive.")
        self._session = session
        self._daily_token_limit = daily_token_limit

    async def reserve(
        self,
        *,
        now: datetime,
        requested_tokens: int,
        job_id: UUID,
        item_id: str,
        provider_profile_id: str,
    ) -> AnswerKeyTokenLease:
        if requested_tokens <= 0:
            raise ValueError("requested_tokens must be positive.")
        utc_day = lease_utc_day(now)
        await self._lock_day(utc_day)
        usage = await self.day_usage(utc_day=utc_day)
        if usage.available_tokens < requested_tokens:
            raise refuse_lease(usage=usage, requested_tokens=requested_tokens)
        model = ExamAnswerKeyTokenLeaseModel(
            id=uuid4(),
            utc_day=utc_day,
            job_id=job_id,
            item_id=item_id,
            provider_profile_id=provider_profile_id,
            reserved_tokens=requested_tokens,
            actual_tokens=None,
            state=AnswerKeyTokenLeaseState.RESERVED.value,
            created_at=now,
            updated_at=now,
        )
        self._session.add(model)
        await self._session.flush()
        return AnswerKeyTokenLease(
            lease_id=model.id,
            utc_day=model.utc_day,
            reserved_tokens=model.reserved_tokens,
            state=AnswerKeyTokenLeaseState.RESERVED,
        )

    async def reconcile(
        self,
        *,
        lease_id: UUID,
        actual_tokens: int,
        now: datetime,
    ) -> None:
        if actual_tokens < 0:
            raise ValueError("actual_tokens cannot be negative.")
        model = await self._session.get(ExamAnswerKeyTokenLeaseModel, lease_id)
        if model is None:
            raise not_found("ExamAnswerKeyTokenLease", str(lease_id))
        if model.state != AnswerKeyTokenLeaseState.RESERVED.value:
            raise ValueError("Only reserved leases can be reconciled.")
        model.actual_tokens = actual_tokens
        model.state = AnswerKeyTokenLeaseState.RECONCILED.value
        model.updated_at = now
        await self._session.flush()

    async def day_usage(self, *, utc_day: date) -> AnswerKeyTokenLeaseDayUsage:
        charged = case(
            (
                ExamAnswerKeyTokenLeaseModel.actual_tokens.is_(None),
                ExamAnswerKeyTokenLeaseModel.reserved_tokens,
            ),
            else_=ExamAnswerKeyTokenLeaseModel.actual_tokens,
        )
        stmt = select(func.coalesce(func.sum(charged), 0)).where(
            ExamAnswerKeyTokenLeaseModel.utc_day == utc_day
        )
        result = await self._session.execute(stmt)
        charged_tokens = int(result.scalar_one())
        return AnswerKeyTokenLeaseDayUsage(
            utc_day=utc_day,
            daily_token_limit=self._daily_token_limit,
            charged_tokens=charged_tokens,
        )

    async def _lock_day(self, utc_day: date) -> None:
        await self._session.execute(select(func.pg_advisory_xact_lock(_day_lock_key(utc_day))))


def _day_lock_key(utc_day: date) -> int:
    digest = hashlib.sha256(f"exam-answer-key-lease:{utc_day.isoformat()}".encode()).digest()
    return int.from_bytes(digest[:8], "big", signed=True)
