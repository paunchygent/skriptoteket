"""Operator lease-status query tests for the answer-key lane.

Purpose:
    Prove the operator read of the current UTC day's lease balance: admin
    role required, allocated/spent/remaining reported from the ledger, and
    an untouched day reads as a full allocation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from skriptoteket.application.curated_apps.handlers.exam_answer_key_lease_status import (
    GetAnswerKeyLeaseStatusHandler,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    AnswerKeyTokenLease,
    AnswerKeyTokenLeaseDayUsage,
    lease_utc_day,
    refuse_lease,
)
from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.identity.models import AuthProvider, Role, User

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 8, 29, 12, 0, 0, tzinfo=UTC)


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class LedgerFake:
    """In-memory lease ledger exposing only the day-usage read."""

    def __init__(self, *, daily_token_limit: int, charged_by_day: dict[date, int]) -> None:
        self._daily_token_limit = daily_token_limit
        self._charged_by_day = charged_by_day

    async def reserve(
        self,
        *,
        now: datetime,
        requested_tokens: int,
        job_id: UUID,
        item_id: str,
        provider_profile_id: str,
    ) -> AnswerKeyTokenLease:
        usage = await self.day_usage(utc_day=lease_utc_day(now))
        raise refuse_lease(usage=usage, requested_tokens=requested_tokens)

    async def reconcile(self, *, lease_id: UUID, actual_tokens: int, now: datetime) -> None:
        raise AssertionError("The status read never reconciles leases.")

    async def day_usage(self, *, utc_day: date) -> AnswerKeyTokenLeaseDayUsage:
        return AnswerKeyTokenLeaseDayUsage(
            utc_day=utc_day,
            daily_token_limit=self._daily_token_limit,
            charged_tokens=self._charged_by_day.get(utc_day, 0),
        )


def _user(*, role: Role) -> User:
    return User(
        id=uuid.uuid4(),
        email=f"{role.value}@example.com",
        role=role,
        auth_provider=AuthProvider.LOCAL,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _handler(*, charged_by_day: dict[date, int]) -> GetAnswerKeyLeaseStatusHandler:
    return GetAnswerKeyLeaseStatusHandler(
        leases=LedgerFake(daily_token_limit=5_000_000, charged_by_day=charged_by_day),
        clock=FixedClock(_NOW),
    )


async def test_admin_reads_the_current_day_balance() -> None:
    handler = _handler(charged_by_day={date(2026, 8, 29): 1_200_000})

    usage = await handler.handle(actor=_user(role=Role.ADMIN))

    assert usage.utc_day == date(2026, 8, 29)
    assert usage.daily_token_limit == 5_000_000
    assert usage.charged_tokens == 1_200_000
    assert usage.available_tokens == 3_800_000


async def test_untouched_day_reads_as_a_full_allocation() -> None:
    handler = _handler(charged_by_day={})

    usage = await handler.handle(actor=_user(role=Role.SUPERUSER))

    assert usage.charged_tokens == 0
    assert usage.available_tokens == 5_000_000


async def test_non_admin_actor_is_refused() -> None:
    handler = _handler(charged_by_day={})

    for role in (Role.USER, Role.CONTRIBUTOR):
        with pytest.raises(DomainError):
            await handler.handle(actor=_user(role=role))
