"""Attempt and lease bookkeeping shared by the answer-key enrichment lanes.

Purpose:
    Record the enrichment attempt together with every candidate's primary
    token lease in one Unit of Work transaction, and reconcile a served
    attempt's lease with the tokens the provider actually used. Both source
    lanes (DigiExam conversion and native exam workspace) run exactly this
    bookkeeping, so it lives here once. Also holds the teacher-facing
    message both lanes use when the model output cannot complete the key.

Relationships:
    Constructed once by
    ``application.curated_apps.handlers.exam_answer_key_enrichment_jobs`` and
    handed to ``exam_answer_key_enrichment_dxe_lane`` and
    ``exam_answer_key_enrichment_workspace_lane``. The per-item provider call
    and failover lease live in ``exam_answer_key_provider_attempts``.
"""

from __future__ import annotations

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    record_enrichment_attempt,
)
from skriptoteket.application.curated_apps.handlers.exam_answer_key_provider_attempts import (
    ProviderAttempt,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    AnswerKeyTokenLease,
    requested_lease_tokens,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import (
    AnswerKeyTokenLeaseRepositoryProtocol,
    ExamAnswerKeyEnrichmentJobRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol

MANUAL_COMPLETION_MESSAGE = (
    "Provet kunde inte kompletteras automatiskt med facit. "
    "Komplettera facit manuellt och försök igen."
)


class AnswerKeyAttemptLedger:
    """Atomic attempt-plus-lease recording and post-call lease reconciliation."""

    def __init__(
        self,
        *,
        enrichment_jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        leases: AnswerKeyTokenLeaseRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._enrichment_jobs = enrichment_jobs
        self._leases = leases
        self._uow = uow
        self._clock = clock

    async def record_attempt_and_reserve(
        self,
        *,
        job: ExamAnswerKeyEnrichmentJob,
        requests: tuple[tuple[str, StructuredLLMRequest], ...],
        profile: StructuredLLMProviderProfile,
    ) -> tuple[ExamAnswerKeyEnrichmentJob, dict[str, AnswerKeyTokenLease]]:
        """Reserve every candidate's lease with the recorded attempt, atomically.

        A refusal aborts the transaction, so an exhausted day records neither
        an attempt nor any partial reservation and no provider call is made.
        """

        now = self._clock.now()
        leases_by_item: dict[str, AnswerKeyTokenLease] = {}
        async with self._uow:
            updated_job = await self._enrichment_jobs.update(
                job=record_enrichment_attempt(job=job, now=now)
            )
            for item_id, request in requests:
                leases_by_item[item_id] = await self._leases.reserve(
                    now=now,
                    requested_tokens=requested_lease_tokens(
                        estimated_input_tokens=request.estimated_input_tokens,
                        max_output_tokens=request.max_output_tokens,
                    ),
                    job_id=updated_job.id,
                    item_id=item_id,
                    provider_profile_id=profile.provider_id,
                )
        return updated_job, leases_by_item

    async def reconcile_attempt_usage(self, *, attempt: ProviderAttempt) -> None:
        usable_tokens = attempt.response.usage.usable_total_tokens
        if usable_tokens is None:
            return
        now = self._clock.now()
        async with self._uow:
            await self._leases.reconcile(
                lease_id=attempt.lease.lease_id,
                actual_tokens=usable_tokens,
                now=now,
            )
