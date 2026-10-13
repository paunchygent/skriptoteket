"""Native exam workspace lane of the answer-key enrichment processor.

Purpose:
    Complete one claimed workspace suggestion job on the answer-key views
    the editor sent with the request (TASK-SKRIPT-39-04-07): reserve the
    daily token leases with the recorded attempt, collect one suggestion
    per requested question (one GLM failover per item after a transient
    outage), and store the suggestions on the job itself. This lane never
    reads a saved document revision, never calls the conversion producer
    and writes no overlay; any failure finishes the job as FAILED with a
    typed ``last_error``.

Relationships:
    Dispatched by
    ``application.curated_apps.handlers.exam_answer_key_enrichment_jobs``,
    which also calls ``fail`` for an expired worker lease. Shares
    ``exam_answer_key_enrichment_attempts`` (attempt and lease bookkeeping
    and the per-item proposal loop) with
    ``exam_answer_key_enrichment_dxe_lane``.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import ValidationError

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    finish_enrichment_job,
)
from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceAnswerKeySuggestionItem,
)
from skriptoteket.application.curated_apps.handlers.exam_answer_key_enrichment_attempts import (
    AnswerKeyAttemptLedger,
)
from skriptoteket.application.curated_apps.handlers.exam_answer_key_provider_attempts import (
    AnswerKeyAttemptCandidate,
    ProviderAttempt,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_enrichment import (
    WorkspaceAnswerKeyRequestPayload,
    WorkspaceAnswerKeySuggestionsPayload,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    AnswerKeyTokenLeaseRefused,
)
from skriptoteket.domain.curated_apps.exam_workspace.answer_key_prompts import (
    WorkspaceAnswerKeyCandidatePlan,
    plan_workspace_answer_key_candidates,
)
from skriptoteket.domain.curated_apps.exam_workspace.answer_key_view import (
    proposal_from_model_content,
    suggestion_from_proposal,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKeySuggestion,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import (
    AnswerKeyProviderSelectorProtocol,
    ExamAnswerKeyEnrichmentJobRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class ExamAnswerKeyEnrichmentWorkspaceLane:
    """Process one editor-sent workspace suggestion job to a terminal status."""

    def __init__(
        self,
        *,
        enrichment_jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        provider_selector: AnswerKeyProviderSelectorProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        ledger: AnswerKeyAttemptLedger,
    ) -> None:
        self._enrichment_jobs = enrichment_jobs
        self._provider_selector = provider_selector
        self._uow = uow
        self._clock = clock
        self._ledger = ledger

    async def handle(self, *, job: ExamAnswerKeyEnrichmentJob) -> ExamAnswerKeyEnrichmentJob:
        """Complete one workspace-lane job: suggestions on the job, no overlay."""

        if job.workspace_lineage_id is None:
            return await self.fail(job=job, last_error="workspace_binding_missing")
        if job.workspace_request_json is None:
            return await self.fail(job=job, last_error="workspace_request_missing")
        try:
            request = WorkspaceAnswerKeyRequestPayload.model_validate(job.workspace_request_json)
        except ValidationError:
            return await self.fail(job=job, last_error="workspace_request_invalid")
        views = request.views
        if not views:
            return await self.fail(job=job, last_error="workspace_no_enrichable_items")

        route = self._provider_selector.select_route()
        plans = plan_workspace_answer_key_candidates(
            job_id=str(job.id),
            views=views,
            profile=route.primary,
        )
        attempt_candidates = tuple(
            _workspace_attempt_candidate(job_id=job.id, plan=plan) for plan in plans
        )
        try:
            job, leases_by_item = await self._ledger.record_attempt_and_reserve(
                job=job,
                requests=tuple(
                    (candidate.item_id, candidate.request) for candidate in attempt_candidates
                ),
                profile=route.primary,
            )
        except AnswerKeyTokenLeaseRefused:
            return await self.fail(job=job, last_error="daily_token_lease_exhausted")

        collected = await self._ledger.collect_valid_proposals(
            job=job,
            route=route,
            plans=plans,
            attempt_candidates=attempt_candidates,
            leases_by_item=leases_by_item,
            proposal_from=_workspace_suggestion,
        )
        suggestions = collected.proposals
        payload = WorkspaceAnswerKeySuggestionsPayload(
            suggestions=tuple(
                ExamWorkspaceAnswerKeySuggestionItem(item_id=item_id, suggestion=suggestion)
                for item_id, suggestion in suggestions
            )
        )
        if collected.failure is not None:
            # The batch ended on a real provider failure: keep every valid
            # suggestion collected before it on the job, and still report
            # the failure truthfully.
            return await self.fail(
                job=job,
                last_error=collected.failure.last_error,
                suggestions=payload if suggestions else None,
            )
        if not suggestions:
            return await self.fail(job=job, last_error="llm_output_invalid")
        now = self._clock.now()
        async with self._uow:
            return await self._enrichment_jobs.update(
                job=finish_enrichment_job(
                    job=job.model_copy(
                        update={
                            "workspace_suggestions_json": payload.model_dump(mode="json"),
                        }
                    ),
                    status=ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED,
                    now=now,
                ),
                expected_worker_id=job.locked_by,
            )

    async def fail(
        self,
        *,
        job: ExamAnswerKeyEnrichmentJob,
        last_error: str,
        suggestions: WorkspaceAnswerKeySuggestionsPayload | None = None,
    ) -> ExamAnswerKeyEnrichmentJob:
        """Finish one workspace-lane job as FAILED; no conversion to update.

        Suggestions collected before the failure stay on the job so the
        status read can still deliver them to the editor.
        """

        if suggestions is not None:
            job = job.model_copy(
                update={"workspace_suggestions_json": suggestions.model_dump(mode="json")}
            )
        now = self._clock.now()
        async with self._uow:
            return await self._enrichment_jobs.update(
                job=finish_enrichment_job(
                    job=job,
                    status=ExamAnswerKeyEnrichmentJobStatus.FAILED,
                    now=now,
                    last_error=last_error,
                ),
                expected_worker_id=job.locked_by,
            )


def _workspace_attempt_candidate(
    *,
    job_id: UUID,
    plan: WorkspaceAnswerKeyCandidatePlan,
) -> AnswerKeyAttemptCandidate:
    """Wrap one workspace candidate plan with its failover request rebuild."""

    view = plan.view

    def build(profile: StructuredLLMProviderProfile) -> StructuredLLMRequest:
        return plan_workspace_answer_key_candidates(
            job_id=str(job_id),
            views=(view,),
            profile=profile,
        )[0].request

    return AnswerKeyAttemptCandidate(
        item_id=view.item_id,
        request=plan.request,
        build_request_for_profile=build,
    )


def _workspace_suggestion(
    plan: WorkspaceAnswerKeyCandidatePlan,
    attempt: ProviderAttempt,
) -> NativeAnswerKeySuggestion | None:
    """Turn one model answer into the suggestion kept on the question."""

    proposal = proposal_from_model_content(
        view=plan.view,
        content=attempt.response.content,
    )
    if proposal is None:
        return None
    return suggestion_from_proposal(
        view=plan.view,
        proposal=proposal,
        provider_profile_id=attempt.profile.provider_id,
        model=attempt.profile.model,
        prompt_template_version=plan.request.prompt_template_version,
    )
