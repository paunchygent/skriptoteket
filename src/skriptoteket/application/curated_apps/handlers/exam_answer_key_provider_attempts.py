"""Per-item provider-attempt orchestration for answer-key enrichment.

Purpose:
    Run one candidate's provider attempt for the enrichment job processor:
    call the primary profile once and, only after a transient outage, make
    exactly one failover attempt under its own second lease from the same
    daily counter. A lease refusal is the exhaustion hard stop: the failover
    provider is never called. Leases are never refunded.

Relationships:
    Consumed by
    ``application.curated_apps.handlers.exam_answer_key_enrichment_jobs``;
    the transient-outage gate lives in
    ``domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_completion import (
    AnswerKeyCandidatePlan,
    plan_answer_key_candidates,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    AnswerKeyProviderRoute,
    StructuredLLMProviderError,
    StructuredLLMProviderProfile,
    StructuredLLMResponse,
    allows_answer_key_provider_failover,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    AnswerKeyTokenLease,
    AnswerKeyTokenLeaseRefused,
    requested_lease_tokens,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ir_contracts import (
    DigiExamIrItem,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import (
    AnswerKeyStructuredProviderProtocol,
    AnswerKeyTokenLeaseRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = logging.getLogger(__name__)

_PROVIDER_FAILURE_MESSAGE = "Facitförslaget kunde inte hämtas just nu. Försök igen senare."


@dataclass(frozen=True)
class EnrichmentFailure:
    """Terminal per-job failure with the teacher-facing message."""

    teacher_message: str
    last_error: str


@dataclass(frozen=True)
class ProviderAttempt:
    """One successful provider attempt with the lease it must reconcile."""

    response: StructuredLLMResponse
    lease: AnswerKeyTokenLease
    profile: StructuredLLMProviderProfile


def lease_exhausted_message(refusal: AnswerKeyTokenLeaseRefused) -> str:
    """Render the teacher-facing exhaustion message with the UTC reset time."""

    return (
        "Dagens AI-budget för facitförslag är förbrukad. Försök igen efter "
        f"{refusal.resets_at:%Y-%m-%d %H:%M} UTC."
    )


class AnswerKeyProviderAttemptRunner:
    """Execute one candidate's primary attempt with the single failover."""

    def __init__(
        self,
        *,
        provider: AnswerKeyStructuredProviderProtocol,
        leases: AnswerKeyTokenLeaseRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._provider = provider
        self._leases = leases
        self._uow = uow
        self._clock = clock

    async def attempt_with_failover(
        self,
        *,
        job: ExamAnswerKeyEnrichmentJob,
        candidate: AnswerKeyCandidatePlan,
        route: AnswerKeyProviderRoute,
        primary_lease: AnswerKeyTokenLease,
    ) -> ProviderAttempt | EnrichmentFailure:
        """Call the primary once; fail over exactly once on a transient outage."""

        try:
            response = await self._provider.complete_structured(
                request=candidate.request,
                profile=route.primary,
            )
        except StructuredLLMProviderError as exc:
            _log_provider_failure(item_id=candidate.item.item_id, error=exc)
            if not allows_answer_key_provider_failover(exc):
                return EnrichmentFailure(
                    teacher_message=_PROVIDER_FAILURE_MESSAGE,
                    last_error=exc.failure_code.value,
                )
            return await self._attempt_failover(job=job, item=candidate.item, route=route)
        return ProviderAttempt(response=response, lease=primary_lease, profile=route.primary)

    async def _attempt_failover(
        self,
        *,
        job: ExamAnswerKeyEnrichmentJob,
        item: DigiExamIrItem,
        route: AnswerKeyProviderRoute,
    ) -> ProviderAttempt | EnrichmentFailure:
        """Attempt the failover profile once with its own second lease.

        The second reservation draws from the same daily counter. A refusal
        here is the exhaustion hard stop: the failover provider is never
        called and the job fails closed. The primary lease stays charged
        either way; leases are never refunded.
        """

        candidate = plan_answer_key_candidates(
            job_id=str(job.conversion_job_id),
            items=(item,),
            profile=route.failover,
        )[0]
        now = self._clock.now()
        try:
            async with self._uow:
                lease = await self._leases.reserve(
                    now=now,
                    requested_tokens=requested_lease_tokens(
                        estimated_input_tokens=candidate.request.estimated_input_tokens,
                        max_output_tokens=candidate.request.max_output_tokens,
                    ),
                    job_id=job.id,
                    item_id=item.item_id,
                    provider_profile_id=route.failover.provider_id,
                )
        except AnswerKeyTokenLeaseRefused as refusal:
            return EnrichmentFailure(
                teacher_message=lease_exhausted_message(refusal),
                last_error="daily_token_lease_exhausted",
            )
        try:
            response = await self._provider.complete_structured(
                request=candidate.request,
                profile=route.failover,
            )
        except StructuredLLMProviderError as exc:
            _log_provider_failure(item_id=item.item_id, error=exc)
            return EnrichmentFailure(
                teacher_message=_PROVIDER_FAILURE_MESSAGE,
                last_error=exc.failure_code.value,
            )
        return ProviderAttempt(response=response, lease=lease, profile=route.failover)


def _log_provider_failure(*, item_id: str, error: StructuredLLMProviderError) -> None:
    logger.warning(
        "Answer-key provider attempt failed",
        extra={
            "item_id": item_id,
            "provider_id": error.provider_id,
            "failure_code": error.failure_code.value,
            "status_code": error.status_code,
        },
    )
