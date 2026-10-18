"""Attempt and lease bookkeeping shared by the answer-key enrichment lanes.

Purpose:
    Record the enrichment attempt together with every candidate's primary
    token lease in one Unit of Work transaction, then collect one proposal
    per candidate: call the provider (with failover), reconcile the served
    attempt's lease with the tokens the provider actually used, and let the
    lane turn the model output into its proposal. The source lanes run
    exactly this bookkeeping and loop, so it lives here once. Also holds
    the teacher-facing message the lanes use when the model output cannot
    complete the key.

Relationships:
    Constructed once by
    ``application.curated_apps.handlers.exam_answer_key_enrichment_jobs`` and
    handed to ``exam_answer_key_enrichment_workspace_lane``. The per-item provider call
    and failover lease live in ``exam_answer_key_provider_attempts``.
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
    AnswerKeyProviderRoute,
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
    """Atomic attempt-plus-lease recording and the per-candidate proposal loop."""

    def __init__(
        self,
        *,
        enrichment_jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        leases: AnswerKeyTokenLeaseRepositoryProtocol,
        attempts: AnswerKeyProviderAttemptRunner,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._enrichment_jobs = enrichment_jobs
        self._leases = leases
        self._attempts = attempts
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

    async def collect_proposals[P, R](
        self,
        *,
        job: ExamAnswerKeyEnrichmentJob,
        route: AnswerKeyProviderRoute,
        plans: tuple[P, ...],
        attempt_candidates: tuple[AnswerKeyAttemptCandidate, ...],
        leases_by_item: dict[str, AnswerKeyTokenLease],
        proposal_from: Callable[[P, ProviderAttempt], R | None],
    ) -> tuple[tuple[R, ...], StructuredLLMProviderProfile] | EnrichmentFailure:
        """Collect one proposal per candidate plan, in plan order.

        Returns the proposals with the profile that served them (the failover
        once any item fell over), or the first failure: a provider failure, or
        ``llm_output_invalid`` when ``proposal_from`` rejects the model output.
        """

        proposals: list[R] = []
        serving_profile = route.primary
        for plan, candidate in zip(plans, attempt_candidates, strict=True):
            attempt = await self._attempts.attempt_with_failover(
                job=job,
                candidate=candidate,
                route=route,
                primary_lease=leases_by_item[candidate.item_id],
            )
            if isinstance(attempt, EnrichmentFailure):
                return attempt
            if attempt.profile is route.failover:
                serving_profile = route.failover
            await self._reconcile_attempt_usage(attempt=attempt)
            proposal = proposal_from(plan, attempt)
            if proposal is None:
                return EnrichmentFailure(
                    teacher_message=MANUAL_COMPLETION_MESSAGE,
                    last_error="llm_output_invalid",
                )
            proposals.append(proposal)
        return tuple(proposals), serving_profile

    async def collect_valid_proposals[P, R](
        self,
        *,
        job: ExamAnswerKeyEnrichmentJob,
        route: AnswerKeyProviderRoute,
        plans: tuple[P, ...],
        attempt_candidates: tuple[AnswerKeyAttemptCandidate, ...],
        leases_by_item: dict[str, AnswerKeyTokenLease],
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
        serving_profile = route.primary
        saw_invalid_output = False
        for plan, candidate in zip(plans, attempt_candidates, strict=True):
            attempt = await self._attempts.attempt_with_failover(
                job=job,
                candidate=candidate,
                route=route,
                primary_lease=leases_by_item[candidate.item_id],
            )
            if isinstance(attempt, EnrichmentFailure):
                return ValidProposalCollection(
                    proposals=tuple(proposals),
                    serving_profile=serving_profile,
                    failure=attempt,
                    saw_invalid_output=saw_invalid_output,
                )
            if attempt.profile is route.failover:
                serving_profile = route.failover
            await self._reconcile_attempt_usage(attempt=attempt)
            proposal = proposal_from(plan, attempt)
            if proposal is None:
                saw_invalid_output = True
                continue
            proposals.append((candidate.item_id, proposal))
        return ValidProposalCollection(
            proposals=tuple(proposals),
            serving_profile=serving_profile,
            failure=None,
            saw_invalid_output=saw_invalid_output,
        )

    async def _reconcile_attempt_usage(self, *, attempt: ProviderAttempt) -> None:
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
