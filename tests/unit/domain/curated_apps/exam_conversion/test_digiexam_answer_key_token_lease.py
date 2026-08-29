"""Tests for answer-key daily token-lease domain rules.

Purpose:
    Pin the non-refundable lease accounting ported from sir-convert-a-lot
    `76983339`: reserve-before-call sizing, no refunds, structural UTC-day
    partitioning, and the typed refusal that carries the UTC reset time.

Relationships:
    - Exercises `domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease`.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    AnswerKeyTokenLeaseDayUsage,
    charged_lease_tokens,
    lease_reset_time,
    lease_utc_day,
    refuse_lease,
    requested_lease_tokens,
)

pytestmark = pytest.mark.unit

_LATE_FIRST_DAY = datetime(2026, 8, 29, 23, 59, tzinfo=UTC)
_SECOND_DAY_MIDNIGHT = datetime(2026, 8, 30, 0, 0, tzinfo=UTC)


def test_requested_tokens_reserve_full_input_and_output_allowance() -> None:
    assert requested_lease_tokens(estimated_input_tokens=100, max_output_tokens=200) == 300


def test_requested_tokens_reject_invalid_allowances() -> None:
    with pytest.raises(ValueError):
        requested_lease_tokens(estimated_input_tokens=-1, max_output_tokens=200)
    with pytest.raises(ValueError):
        requested_lease_tokens(estimated_input_tokens=10, max_output_tokens=0)


def test_unreconciled_lease_charges_reserved_tokens_without_refund() -> None:
    assert charged_lease_tokens(reserved_tokens=300, actual_tokens=None) == 300


def test_reconciled_lease_charges_provider_reported_usage() -> None:
    assert charged_lease_tokens(reserved_tokens=300, actual_tokens=240) == 240


def test_utc_day_partitions_structurally_at_midnight() -> None:
    assert lease_utc_day(_LATE_FIRST_DAY) == date(2026, 8, 29)
    assert lease_utc_day(_SECOND_DAY_MIDNIGHT) == date(2026, 8, 30)


def test_utc_day_normalizes_non_utc_clock_offsets() -> None:
    stockholm_like = datetime(2026, 8, 30, 1, 30, tzinfo=timezone(timedelta(hours=2)))
    assert lease_utc_day(stockholm_like) == date(2026, 8, 29)


def test_utc_day_requires_timezone_aware_clock() -> None:
    with pytest.raises(ValueError):
        lease_utc_day(datetime(2026, 8, 29, 23, 59))


def test_refusal_carries_utc_reset_time_and_available_balance() -> None:
    usage = AnswerKeyTokenLeaseDayUsage(
        utc_day=date(2026, 8, 29),
        daily_token_limit=100,
        charged_tokens=60,
    )

    refusal = refuse_lease(usage=usage, requested_tokens=50)

    assert refusal.utc_day == date(2026, 8, 29)
    assert refusal.requested_tokens == 50
    assert refusal.available_tokens == 40
    assert refusal.resets_at == datetime(2026, 8, 30, 0, 0, tzinfo=UTC)


def test_available_tokens_never_report_below_zero() -> None:
    usage = AnswerKeyTokenLeaseDayUsage(
        utc_day=date(2026, 8, 29),
        daily_token_limit=100,
        charged_tokens=140,
    )
    assert usage.available_tokens == 0


def test_reset_time_is_next_utc_midnight() -> None:
    assert lease_reset_time(date(2026, 12, 31)) == datetime(2027, 1, 1, 0, 0, tzinfo=UTC)
