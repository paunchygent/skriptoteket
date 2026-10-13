"""Native exam workspace lane of the answer-key enrichment processor.

Purpose:
    Complete one claimed workspace enrichment job: load the pinned head
    container from Mina filer, reserve the daily token leases with the
    recorded attempt, collect one advisory answer-key proposal per
    enrichable item (one GLM failover per item after a transient outage),
    and persist the proposals payload as the job's proposed overlay. This
    lane never calls the conversion producer and has no conversion job to
    update; any failure finishes the enrichment job as FAILED with a typed
    ``last_error``.

Relationships:
    Dispatched by
    ``application.curated_apps.handlers.exam_answer_key_enrichment_jobs``,
    which also calls ``fail`` for an expired worker lease. Shares
    ``exam_answer_key_enrichment_attempts`` (attempt and lease bookkeeping
    and the per-item proposal loop) with
    ``exam_answer_key_enrichment_dxe_lane``.
"""

from __future__ import annotations

import hashlib
from uuid import UUID

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeyProposedOverlay,
    finish_enrichment_job,
)
from skriptoteket.application.curated_apps.handlers.exam_answer_key_enrichment_attempts import (
    AnswerKeyAttemptLedger,
)
from skriptoteket.application.curated_apps.handlers.exam_answer_key_provider_attempts import (
    AnswerKeyAttemptCandidate,
    EnrichmentFailure,
    ProviderAttempt,
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
    WorkspaceAnswerKeyProposalRecord,
    WorkspaceAnswerKeyProposalsPayload,
    answer_key_item_views,
    proposal_from_model_content,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_json import (
    native_exam_document_json_bytes,
)
from skriptoteket.domain.errors import DomainError
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import (
    AnswerKeyProviderSelectorProtocol,
    ExamAnswerKeyEnrichmentJobRepositoryProtocol,
    ExamAnswerKeyProposedOverlayRepositoryProtocol,
)
from skriptoteket.protocols.exam_workspace import ExamWorkspaceContainerCodecProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol, VaultStorageProtocol


class ExamAnswerKeyEnrichmentWorkspaceLane:
    """Process one native-workspace enrichment job to a terminal status."""

    def __init__(
        self,
        *,
        enrichment_jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        proposed_overlays: ExamAnswerKeyProposedOverlayRepositoryProtocol,
        provider_selector: AnswerKeyProviderSelectorProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        ledger: AnswerKeyAttemptLedger,
        vault_files: VaultFileRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        workspace_codec: ExamWorkspaceContainerCodecProtocol,
    ) -> None:
        self._enrichment_jobs = enrichment_jobs
        self._proposed_overlays = proposed_overlays
        self._provider_selector = provider_selector
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator
        self._ledger = ledger
        self._vault_files = vault_files
        self._vault_storage = vault_storage
        self._workspace_codec = workspace_codec

    async def handle(self, *, job: ExamAnswerKeyEnrichmentJob) -> ExamAnswerKeyEnrichmentJob:
        """Complete one workspace-lane job: advisory proposals, no conversion."""

        if job.workspace_lineage_id is None or job.workspace_document_revision is None:
            return await self.fail(job=job, last_error="workspace_binding_missing")
        head = await self._vault_files.get_document_head(
            user_id=job.owner_user_id,
            document_lineage_id=job.workspace_lineage_id,
        )
        if head is None or head.document_version != job.workspace_document_revision:
            return await self.fail(job=job, last_error="workspace_document_revision_stale")
        content = await self._vault_storage.read_file(user_id=job.owner_user_id, file_id=head.id)
        try:
            container = self._workspace_codec.parse(content=content)
        except DomainError:
            return await self.fail(job=job, last_error="workspace_container_invalid")
        document = container.document
        if (
            document.document_id != job.workspace_lineage_id
            or document.revision != job.workspace_document_revision
        ):
            return await self.fail(job=job, last_error="workspace_container_invalid")
        views = answer_key_item_views(document)
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

        collected = await self._ledger.collect_proposals(
            job=job,
            route=route,
            plans=plans,
            attempt_candidates=attempt_candidates,
            leases_by_item=leases_by_item,
            proposal_from=_workspace_proposal_record,
        )
        if isinstance(collected, EnrichmentFailure):
            return await self.fail(job=job, last_error=collected.last_error)
        records, serving_profile = collected

        payload = WorkspaceAnswerKeyProposalsPayload(
            lineage_id=job.workspace_lineage_id,
            document_revision=job.workspace_document_revision,
            items=records,
        )
        now = self._clock.now()
        async with self._uow:
            await self._proposed_overlays.create(
                proposed_overlay=ExamAnswerKeyProposedOverlay(
                    id=self._id_generator.new_uuid(),
                    enrichment_job_id=job.id,
                    conversion_job_id=None,
                    owner_user_id=job.owner_user_id,
                    workspace_lineage_id=job.workspace_lineage_id,
                    workspace_document_revision=job.workspace_document_revision,
                    source_file_sha256=hashlib.sha256(content).hexdigest(),
                    source_ir_sha256=hashlib.sha256(
                        native_exam_document_json_bytes(document)
                    ).hexdigest(),
                    provider_profile_id=serving_profile.provider_id,
                    model=serving_profile.model,
                    overlay_json=payload.model_dump(mode="json"),
                    created_at=now,
                )
            )
            return await self._enrichment_jobs.update(
                job=finish_enrichment_job(
                    job=job,
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
    ) -> ExamAnswerKeyEnrichmentJob:
        """Finish one workspace-lane job as FAILED; no conversion to update."""

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


def _workspace_proposal_record(
    plan: WorkspaceAnswerKeyCandidatePlan,
    attempt: ProviderAttempt,
) -> WorkspaceAnswerKeyProposalRecord | None:
    """Turn one model answer into the item's advisory proposal record."""

    proposal = proposal_from_model_content(
        view=plan.view,
        content=attempt.response.content,
    )
    if proposal is None:
        return None
    return WorkspaceAnswerKeyProposalRecord(
        item_id=proposal.item_id,
        kind=proposal.kind,
        correct_choice_ids=proposal.correct_choice_ids,
        gap_accepted_values={gap_id: values for gap_id, values in proposal.gap_accepted_values},
        match_pairs=proposal.match_pairs,
        provider_profile_id=attempt.profile.provider_id,
        model=attempt.profile.model,
        prompt_template_version=plan.request.prompt_template_version,
    )
