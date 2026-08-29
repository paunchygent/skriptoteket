"""Daily token-lease domain rules for answer-key provider attempts.

Purpose:
    Define the non-refundable daily token-lease accounting rules ported from
    sir-convert-a-lot `76983339`: reserve before every provider call, never
    refund, and reset structurally at UTC midnight via UTC-day partitioning.

Relationships:
    - The lease is one Postgres table owned through the Unit of Work; the
      repository seam lives in `protocols.exam_answer_key` and the SQL
      implementation in `infrastructure.repositories.exam_answer_key_token_leases`.
    - Consumed by the enrichment worker handler in
      `application.curated_apps.handlers.exam_answer_key_enrichment_jobs`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum
from uuid import UUID


class AnswerKeyTokenLeaseState(StrEnum):
    """Durable state of one non-refundable provider-attempt lease."""

    RESERVED = "reserved"
    RECONCILED = "reconciled"


@dataclass(frozen=True)
class AnswerKeyTokenLease:
    """Persisted reservation state for one provider attempt."""

    lease_id: UUID
    utc_day: date
    reserved_tokens: int
    state: AnswerKeyTokenLeaseState
    actual_tokens: int | None = None


@dataclass(frozen=True)
class AnswerKeyTokenLeaseDayUsage:
    """Aggregated non-refundable accounting for one UTC day."""

    utc_day: date
    daily_token_limit: int
    charged_tokens: int

    @property
    def available_tokens(self) -> int:
        """Tokens that remain admissible before the daily limit is reached."""

        return max(0, self.daily_token_limit - self.charged_tokens)


@dataclass(frozen=True)
class AnswerKeyTokenLeaseRefused(Exception):
    """Typed fail-closed lease refusal carrying the UTC reset time."""

    utc_day: date
    requested_tokens: int
    available_tokens: int
    resets_at: datetime

    def __str__(self) -> str:
        return (
            f"Answer-key daily token lease is exhausted; it resets at {self.resets_at.isoformat()}."
        )


def lease_utc_day(now: datetime) -> date:
    """Return the structural UTC-day partition key for one instant."""

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Lease clock must supply a timezone-aware datetime.")
    return now.astimezone(UTC).date()


def lease_reset_time(utc_day: date) -> datetime:
    """Return the UTC midnight at which the given lease day resets."""

    return datetime.combine(utc_day + timedelta(days=1), time.min, tzinfo=UTC)


def requested_lease_tokens(*, estimated_input_tokens: int, max_output_tokens: int) -> int:
    """Return a request's full reserved allowance before provider I/O."""

    if estimated_input_tokens < 0:
        raise ValueError("estimated_input_tokens cannot be negative.")
    if max_output_tokens <= 0:
        raise ValueError("max_output_tokens must be positive.")
    return estimated_input_tokens + max_output_tokens


def charged_lease_tokens(*, reserved_tokens: int, actual_tokens: int | None) -> int:
    """Return the tokens one lease charges against its day, never refunded."""

    if actual_tokens is None:
        return reserved_tokens
    return actual_tokens


def refuse_lease(
    *,
    usage: AnswerKeyTokenLeaseDayUsage,
    requested_tokens: int,
) -> AnswerKeyTokenLeaseRefused:
    """Build the typed refusal for one over-limit reservation attempt."""

    return AnswerKeyTokenLeaseRefused(
        utc_day=usage.utc_day,
        requested_tokens=requested_tokens,
        available_tokens=usage.available_tokens,
        resets_at=lease_reset_time(usage.utc_day),
    )
