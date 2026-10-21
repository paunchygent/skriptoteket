"""Attempt bookkeeping shared by the answer-key enrichment lanes.

Purpose:
    Record the enrichment attempt in one Unit of Work transaction, then
    collect one proposal per candidate: call the provider through the door
    and let the lane turn the model output into its proposal. The source
    lanes run exactly this bookkeeping and loop, so it lives here once.
    Also holds the teacher-facing message the lanes use when the model
    output cannot complete the key.

Relationships:
    Constructed once by
    ``application.curated_apps.handlers.exam_answer_key_enrichment_jobs`` and
    handed to ``exam_answer_key_enrichment_workspace_lane``. The per-item provider call
    lives in ``exam_answer_key_provider_attempts``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    record_enrichment_attempt,
)
from skriptoteket.application.curated_apps.handlers.exam_answer_key_provider_attempts import (
    AnswerKeyAttemptCandidate,
    AnswerKeyProviderAttemptRunner,
    EnrichmentFailure,
    ProviderAttempt,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
)
from skriptoteket.domain.llm_door import AiDoorCaller
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import (
    ExamAnswerKeyEnrichmentJobRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


@dataclass(frozen=True)
class ValidProposalCollection[R]:
    """Workspace collection outcome: valid proposals plus how the batch ended.

    ``failure`` is the terminal provider failure that stopped the batch, if
    any; ``proposals`` holds every valid answer collected before it (or all
    of them when the batch ran to completion). ``saw_invalid_output`` tells
    an all-invalid batch (no proposals, no failure) apart from success.
    """

    proposals: tuple[tuple[str, R], ...]
    serving_profile: StructuredLLMProviderProfile
    failure: EnrichmentFailure | None
    saw_invalid_output: bool


MANUAL_COMPLETION_MESSAGE = (
    "Provet kunde inte kompletteras automatiskt med facit. "
    "Komplettera facit manuellt och försök igen."
)


class AnswerKeyAttemptLedger:
    """Atomic attempt recording and the per-candidate proposal loop."""

    def __init__(
        self,
        *,
        enrichment_jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        attempts: AnswerKeyProviderAttemptRunner,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._enrichment_jobs = enrichment_jobs
        self._attempts = attempts
        self._uow = uow
        self._clock = clock

    async def record_attempt(
        self, *, job: ExamAnswerKeyEnrichmentJob
    ) -> ExamAnswerKeyEnrichmentJob:
        """Record the attempt this job is about to make, atomically."""

        now = self._clock.now()
        async with self._uow:
            return await self._enrichment_jobs.update(
                job=record_enrichment_attempt(job=job, now=now)
            )

    async def collect_proposals[P, R](
        self,
        *,
        job: ExamAnswerKeyEnrichmentJob,
        profile: StructuredLLMProviderProfile,
        caller: AiDoorCaller,
        plans: tuple[P, ...],
        attempt_candidates: tuple[AnswerKeyAttemptCandidate, ...],
        proposal_from: Callable[[P, ProviderAttempt], R | None],
    ) -> tuple[tuple[R, ...], StructuredLLMProviderProfile] | EnrichmentFailure:
        """Collect one proposal per candidate plan, in plan order.

        Returns the proposals with the profile that served them, or the
        first failure: a provider failure, or ``llm_output_invalid`` when
        ``proposal_from`` rejects the model output.
        """

        proposals: list[R] = []
        for plan, candidate in zip(plans, attempt_candidates, strict=True):
            attempt = await self._attempts.attempt(
                job=job,
                candidate=candidate,
                profile=profile,
                caller=caller,
            )
            if isinstance(attempt, EnrichmentFailure):
                return attempt
            proposal = proposal_from(plan, attempt)
            if proposal is None:
                return EnrichmentFailure(
                    teacher_message=MANUAL_COMPLETION_MESSAGE,
                    last_error="llm_output_invalid",
                )
            proposals.append(proposal)
        return tuple(proposals), profile

    async def collect_valid_proposals[P, R](
        self,
        *,
        job: ExamAnswerKeyEnrichmentJob,
        profile: StructuredLLMProviderProfile,
        caller: AiDoorCaller,
        plans: tuple[P, ...],
        attempt_candidates: tuple[AnswerKeyAttemptCandidate, ...],
        proposal_from: Callable[[P, ProviderAttempt], R | None],
    ) -> ValidProposalCollection[R]:
        """Collect every valid proposal, keyed by its candidate's item id.

        Workspace-only policy: one question's invalid model output neither
        discards the valid proposals already collected nor stops the later
        questions; processing continues in plan order. A provider failure
        stops the collection at once (no further calls), but the valid
        proposals already collected travel with the failure so the lane can
        keep and deliver them while still reporting the real failure. The
        DigiExam lane keeps the all-or-nothing ``collect_proposals`` above.
        """

        proposals: list[tuple[str, R]] = []
        saw_invalid_output = False
        for plan, candidate in zip(plans, attempt_candidates, strict=True):
            attempt = await self._attempts.attempt(
                job=job,
                candidate=candidate,
                profile=profile,
                caller=caller,
            )
            if isinstance(attempt, EnrichmentFailure):
                return ValidProposalCollection(
                    proposals=tuple(proposals),
                    serving_profile=profile,
                    failure=attempt,
                    saw_invalid_output=saw_invalid_output,
                )
            proposal = proposal_from(plan, attempt)
            if proposal is None:
                saw_invalid_output = True
                continue
            proposals.append((candidate.item_id, proposal))
        return ValidProposalCollection(
            proposals=tuple(proposals),
            serving_profile=profile,
            failure=None,
            saw_invalid_output=saw_invalid_output,
        )
