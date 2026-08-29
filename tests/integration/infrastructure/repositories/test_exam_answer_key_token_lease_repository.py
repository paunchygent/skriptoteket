"""Integration tests for the Postgres answer-key token lease.

Purpose:
    Prove the single-table lease semantics against real Postgres: reserve
    before the call, typed refusal on exhaustion with the UTC reset time,
    no refunds for unreconciled leases, and the structural UTC-day reset,
    all with an injected clock.

Relationships:
    - Exercises `PostgreSQLAnswerKeyTokenLeaseRepository` under the migrated
      schema from revision `b7d3f1a5c9e2`.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    AnswerKeyTokenLeaseRefused,
    AnswerKeyTokenLeaseState,
)
from skriptoteket.infrastructure.repositories.exam_answer_key_token_leases import (
    PostgreSQLAnswerKeyTokenLeaseRepository,
)

pytestmark = pytest.mark.asyncio(loop_scope="module")

_LATE_FIRST_DAY = datetime(2026, 8, 29, 23, 59, tzinfo=UTC)
_SECOND_DAY = datetime(2026, 8, 30, 0, 0, tzinfo=UTC)


def _repository(
    session: AsyncSession, *, daily_token_limit: int
) -> PostgreSQLAnswerKeyTokenLeaseRepository:
    return PostgreSQLAnswerKeyTokenLeaseRepository(
        session,
        daily_token_limit=daily_token_limit,
    )


async def test_reserve_and_reconcile_move_the_day_charge_to_reported_usage(
    db_session: AsyncSession,
) -> None:
    repository = _repository(db_session, daily_token_limit=1_000)

    lease = await repository.reserve(
        now=_LATE_FIRST_DAY,
        requested_tokens=300,
        job_id=uuid4(),
        item_id="item-001",
        provider_profile_id="openai-gpt-5.6-luna",
    )
    reserved_usage = await repository.day_usage(utc_day=date(2026, 8, 29))
    assert lease.state is AnswerKeyTokenLeaseState.RESERVED
    assert reserved_usage.charged_tokens == 300

    await repository.reconcile(lease_id=lease.lease_id, actual_tokens=240, now=_LATE_FIRST_DAY)
    reconciled_usage = await repository.day_usage(utc_day=date(2026, 8, 29))
    assert reconciled_usage.charged_tokens == 240


async def test_exhaustion_refuses_with_typed_reset_time_and_reserves_nothing(
    db_session: AsyncSession,
) -> None:
    repository = _repository(db_session, daily_token_limit=100)
    await repository.reserve(
        now=_LATE_FIRST_DAY,
        requested_tokens=60,
        job_id=uuid4(),
        item_id="item-001",
        provider_profile_id="openai-gpt-5.6-luna",
    )

    with pytest.raises(AnswerKeyTokenLeaseRefused) as exc_info:
        await repository.reserve(
            now=_LATE_FIRST_DAY,
            requested_tokens=50,
            job_id=uuid4(),
            item_id="item-002",
            provider_profile_id="openai-gpt-5.6-luna",
        )

    refusal = exc_info.value
    assert refusal.available_tokens == 40
    assert refusal.requested_tokens == 50
    assert refusal.utc_day == date(2026, 8, 29)
    assert refusal.resets_at == datetime(2026, 8, 30, 0, 0, tzinfo=UTC)
    usage = await repository.day_usage(utc_day=date(2026, 8, 29))
    assert usage.charged_tokens == 60


async def test_unreconciled_leases_stay_charged_without_refund(
    db_session: AsyncSession,
) -> None:
    repository = _repository(db_session, daily_token_limit=100)
    await repository.reserve(
        now=_LATE_FIRST_DAY,
        requested_tokens=90,
        job_id=uuid4(),
        item_id="item-001",
        provider_profile_id="openai-gpt-5.6-luna",
    )

    usage = await repository.day_usage(utc_day=date(2026, 8, 29))
    assert usage.charged_tokens == 90
    with pytest.raises(AnswerKeyTokenLeaseRefused):
        await repository.reserve(
            now=_LATE_FIRST_DAY,
            requested_tokens=20,
            job_id=uuid4(),
            item_id="item-002",
            provider_profile_id="openai-gpt-5.6-luna",
        )


async def test_utc_day_partition_resets_structurally_at_midnight(
    db_session: AsyncSession,
) -> None:
    repository = _repository(db_session, daily_token_limit=100)
    await repository.reserve(
        now=_LATE_FIRST_DAY,
        requested_tokens=90,
        job_id=uuid4(),
        item_id="item-001",
        provider_profile_id="openai-gpt-5.6-luna",
    )

    second_day_before = await repository.day_usage(utc_day=date(2026, 8, 30))
    assert second_day_before.charged_tokens == 0

    second_day_lease = await repository.reserve(
        now=_SECOND_DAY,
        requested_tokens=90,
        job_id=uuid4(),
        item_id="item-001",
        provider_profile_id="openai-gpt-5.6-luna",
    )
    assert second_day_lease.utc_day == date(2026, 8, 30)
    first_day = await repository.day_usage(utc_day=date(2026, 8, 29))
    second_day = await repository.day_usage(utc_day=date(2026, 8, 30))
    assert first_day.charged_tokens == 90
    assert second_day.charged_tokens == 90
