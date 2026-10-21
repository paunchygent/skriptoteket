"""Per-item provider-attempt orchestration for answer-key enrichment.

Purpose:
    Run one candidate's provider attempt for the enrichment job processor:
    call the primary profile once and, only after a transient outage, make
    exactly one failover attempt.

Relationships:
    Consumed by
    ``application.curated_apps.handlers.exam_answer_key_enrichment_jobs``;
    the transient-outage gate lives in
    ``domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts``.
    Candidates are source-neutral: each carries its planned request plus a
    builder that re-plans the same item's request for the failover profile.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    AnswerKeyProviderRoute,
    StructuredLLMProviderError,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
    allows_answer_key_provider_failover,
)
from skriptoteket.protocols.exam_answer_key import (
    AnswerKeyStructuredProviderProtocol,
)

logger = logging.getLogger(__name__)

_PROVIDER_FAILURE_MESSAGE = "Facitförslaget kunde inte hämtas just nu. Försök igen senare."

RequestForProfileBuilder = Callable[[StructuredLLMProviderProfile], StructuredLLMRequest]


@dataclass(frozen=True)
class EnrichmentFailure:
    """Terminal per-job failure with the teacher-facing message."""

    teacher_message: str
    last_error: str


@dataclass(frozen=True)
class ProviderAttempt:
    """One successful provider attempt."""

    response: StructuredLLMResponse
    profile: StructuredLLMProviderProfile


@dataclass(frozen=True)
class AnswerKeyAttemptCandidate:
    """One item-local attempt: the planned request plus profile rebinding."""

    item_id: str
    request: StructuredLLMRequest
    build_request_for_profile: RequestForProfileBuilder


class AnswerKeyProviderAttemptRunner:
    """Execute one candidate's primary attempt with the single failover."""

    def __init__(self, *, provider: AnswerKeyStructuredProviderProtocol) -> None:
        self._provider = provider

    async def attempt_with_failover(
        self,
        *,
        job: ExamAnswerKeyEnrichmentJob,
        candidate: AnswerKeyAttemptCandidate,
        route: AnswerKeyProviderRoute,
    ) -> ProviderAttempt | EnrichmentFailure:
        """Call the primary once; fail over exactly once on a transient outage."""

        try:
            response = await self._provider.complete_structured(
                request=candidate.request,
                profile=route.primary,
            )
        except StructuredLLMProviderError as exc:
            _log_provider_failure(item_id=candidate.item_id, error=exc)
            if not allows_answer_key_provider_failover(exc):
                return EnrichmentFailure(
                    teacher_message=_PROVIDER_FAILURE_MESSAGE,
                    last_error=exc.failure_code.value,
                )
            return await self._attempt_failover(job=job, candidate=candidate, route=route)
        return ProviderAttempt(response=response, profile=route.primary)

    async def _attempt_failover(
        self,
        *,
        job: ExamAnswerKeyEnrichmentJob,
        candidate: AnswerKeyAttemptCandidate,
        route: AnswerKeyProviderRoute,
    ) -> ProviderAttempt | EnrichmentFailure:
        """Attempt the failover profile once."""

        request = candidate.build_request_for_profile(route.failover)
        try:
            response = await self._provider.complete_structured(
                request=request,
                profile=route.failover,
            )
        except StructuredLLMProviderError as exc:
            _log_provider_failure(item_id=candidate.item_id, error=exc)
            return EnrichmentFailure(
                teacher_message=_PROVIDER_FAILURE_MESSAGE,
                last_error=exc.failure_code.value,
            )
        return ProviderAttempt(response=response, profile=route.failover)


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
