"""Native exam workspace lane of the answer-key enrichment processor.

Purpose:
    Complete one claimed workspace suggestion job on the answer-key views
    the editor sent with the request (TASK-SKRIPT-39-04-07): build the job's
    door caller from its owner, record the attempt, collect one suggestion
    per requested question through the Luna profile, and store the
    suggestions on the job itself. This lane never reads a saved document
    revision and writes no overlay; any failure finishes the job as FAILED
    with a typed ``last_error``.

Relationships:
    Dispatched by
    ``application.curated_apps.handlers.exam_answer_key_enrichment_jobs``,
    which also calls ``fail`` for an expired worker lease. Shares
    ``exam_answer_key_enrichment_attempts`` (attempt and lease bookkeeping
    and the per-item proposal loop).
"""

from __future__ import annotations

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
)
from skriptoteket.domain.curated_apps.exam_workspace.answer_key_prompts import (
    WorkspaceAnswerKeyCandidatePlan,
    plan_workspace_answer_key_candidates,
)
from skriptoteket.domain.curated_apps.exam_workspace.answer_key_view import (
    proposal_from_model_content,
    suggestion_from_proposal,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKeySuggestion,
)
from skriptoteket.domain.llm_door import AiDailyLimit, door_caller_for
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import (
    ExamAnswerKeyEnrichmentJobRepositoryProtocol,
)
from skriptoteket.protocols.identity import UserRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class ExamAnswerKeyEnrichmentWorkspaceLane:
    """Process one editor-sent workspace suggestion job to a terminal status."""

    def __init__(
        self,
        *,
        enrichment_jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        users: UserRepositoryProtocol,
        profile: StructuredLLMProviderProfile,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        ledger: AnswerKeyAttemptLedger,
    ) -> None:
        self._enrichment_jobs = enrichment_jobs
        self._users = users
        self._profile = profile
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

        owner = await self._users.get_by_id(job.owner_user_id)
        if owner is None:
            return await self.fail(job=job, last_error="owner_missing")
        caller = door_caller_for(user=owner)

        plans = plan_workspace_answer_key_candidates(
            job_id=str(job.id),
            views=views,
            profile=self._profile,
        )
        attempt_candidates = tuple(
            AnswerKeyAttemptCandidate(item_id=plan.view.item_id, request=plan.request)
            for plan in plans
        )
        job = await self._ledger.record_attempt(job=job)

        collected = await self._ledger.collect_valid_proposals(
            job=job,
            profile=self._profile,
            caller=caller,
            plans=plans,
            attempt_candidates=attempt_candidates,
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
                ai_limit=collected.failure.ai_limit,
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
        ai_limit: AiDailyLimit | None = None,
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
        if ai_limit is not None:
            job = job.model_copy(update={"ai_limit": ai_limit})
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
