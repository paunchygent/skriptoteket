"""Per-item provider attempt for answer-key enrichment.

Purpose:
    Run one candidate's provider attempt for the enrichment job processor:
    call the Luna profile once through the provider door. Door limit and
    overage-cap refusals become a terminal per-job failure carrying the door
    limit; every other provider failure becomes the generic provider message.

Relationships:
    Consumed by
    ``application.curated_apps.handlers.exam_answer_key_enrichment_jobs``.
    Candidates are source-neutral: each carries its planned request.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderError,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
)
from skriptoteket.domain.llm_door import (
    AiDailyLimit,
    AiDailyLimitReached,
    AiDoorCaller,
    AiJobOverageCapReached,
    ai_limit_note,
)
from skriptoteket.protocols.exam_answer_key import (
    AnswerKeyStructuredProviderProtocol,
)

logger = logging.getLogger(__name__)

_PROVIDER_FAILURE_MESSAGE = "Facitförslaget kunde inte hämtas just nu. Försök igen senare."


@dataclass(frozen=True)
class EnrichmentFailure:
    """Terminal per-job failure with the teacher-facing message."""

    teacher_message: str
    last_error: str
    ai_limit: AiDailyLimit | None = None


@dataclass(frozen=True)
class ProviderAttempt:
    """One successful provider attempt."""

    response: StructuredLLMResponse
    profile: StructuredLLMProviderProfile


@dataclass(frozen=True)
class AnswerKeyAttemptCandidate:
    """One item-local attempt: the planned request."""

    item_id: str
    request: StructuredLLMRequest


class AnswerKeyProviderAttemptRunner:
    """Execute one candidate's single provider attempt."""

    def __init__(self, *, provider: AnswerKeyStructuredProviderProtocol) -> None:
        self._provider = provider

    async def attempt(
        self,
        *,
        job: ExamAnswerKeyEnrichmentJob,
        candidate: AnswerKeyAttemptCandidate,
        profile: StructuredLLMProviderProfile,
        caller: AiDoorCaller,
    ) -> ProviderAttempt | EnrichmentFailure:
        """Call the provider once; a door limit ends the job with the limit note."""

        try:
            response = await self._provider.complete_structured(
                request=candidate.request,
                profile=profile,
                caller=caller,
            )
        except AiDailyLimitReached as exc:
            return EnrichmentFailure(
                teacher_message=ai_limit_note(exc.limit),
                last_error="ai_daily_limit",
                ai_limit=exc.limit,
            )
        except AiJobOverageCapReached:
            return EnrichmentFailure(
                teacher_message=ai_limit_note(AiDailyLimit.POOL),
                last_error="ai_overage_cap",
                ai_limit=AiDailyLimit.POOL,
            )
        except StructuredLLMProviderError as exc:
            _log_provider_failure(item_id=candidate.item_id, error=exc)
            return EnrichmentFailure(
                teacher_message=_PROVIDER_FAILURE_MESSAGE,
                last_error=exc.failure_code.value,
            )
        return ProviderAttempt(response=response, profile=profile)


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
