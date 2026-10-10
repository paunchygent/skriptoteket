"""Copy pending workspace proposals into a saved revision's existing ledger.

The document store invokes this inside its save Unit of Work. A carried
revision gets a terminal, zero-attempt job and its own overlay so ordinary
revision status lookups keep working without queuing provider execution.
The original overlay and provider provenance remain immutable.
"""

from uuid import UUID

from pydantic import ValidationError

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeyProposedOverlay,
    ExamAnswerKeySourceKind,
)
from skriptoteket.domain.curated_apps.exam_workspace.answer_key_view import (
    WorkspaceAnswerKeyProposalsPayload,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.proposal_carry_forward import (
    carry_pending_proposal_records,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import (
    ExamAnswerKeyEnrichmentJobRepositoryProtocol,
    ExamAnswerKeyProposedOverlayRepositoryProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol


class CarryExamWorkspaceProposals:
    """Persist a filtered copy while the caller owns the save transaction."""

    def __init__(
        self,
        *,
        enrichment_jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        proposed_overlays: ExamAnswerKeyProposedOverlayRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._enrichment_jobs = enrichment_jobs
        self._proposed_overlays = proposed_overlays
        self._clock = clock
        self._id_generator = id_generator

    async def carry(
        self,
        *,
        owner_user_id: UUID,
        previous_document: NativeExamDocument,
        document: NativeExamDocument,
        rejected_item_ids: frozenset[str],
    ) -> None:
        job = await self._enrichment_jobs.get_by_workspace_revision(
            owner_user_id=owner_user_id,
            workspace_lineage_id=previous_document.document_id,
            workspace_document_revision=previous_document.revision,
        )
        if job is None or job.status is not ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED:
            return
        overlay = await self._proposed_overlays.get_by_enrichment_job_id(enrichment_job_id=job.id)
        if (
            overlay is None
            or overlay.owner_user_id != owner_user_id
            or overlay.workspace_lineage_id != previous_document.document_id
            or overlay.workspace_document_revision != previous_document.revision
        ):
            return
        try:
            payload = WorkspaceAnswerKeyProposalsPayload.model_validate(overlay.overlay_json)
        except ValidationError:
            return
        records = carry_pending_proposal_records(
            previous_document=previous_document,
            document=document,
            payload=payload,
            rejected_item_ids=rejected_item_ids,
        )
        if not records:
            return

        now = self._clock.now()
        carried_job = await self._enrichment_jobs.create(
            job=ExamAnswerKeyEnrichmentJob(
                id=self._id_generator.new_uuid(),
                source_kind=ExamAnswerKeySourceKind.WORKSPACE,
                owner_user_id=owner_user_id,
                status=ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED,
                input_filename=job.input_filename,
                workspace_lineage_id=document.document_id,
                workspace_document_revision=document.revision,
                available_at=now,
                created_at=now,
                updated_at=now,
                finished_at=now,
            )
        )
        carried_payload = WorkspaceAnswerKeyProposalsPayload(
            lineage_id=document.document_id,
            document_revision=document.revision,
            items=records,
        )
        await self._proposed_overlays.create(
            proposed_overlay=ExamAnswerKeyProposedOverlay(
                id=self._id_generator.new_uuid(),
                enrichment_job_id=carried_job.id,
                owner_user_id=owner_user_id,
                workspace_lineage_id=document.document_id,
                workspace_document_revision=document.revision,
                source_file_sha256=overlay.source_file_sha256,
                source_ir_sha256=overlay.source_ir_sha256,
                provider_profile_id=overlay.provider_profile_id,
                model=overlay.model,
                overlay_json=carried_payload.model_dump(mode="json"),
                created_at=now,
            )
        )
