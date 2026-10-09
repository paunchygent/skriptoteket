"""Exam workspace answer-key enrichment: enqueue and status handlers.

Purpose:
    Start one advisory machine answer-key enrichment job for a native exam
    workspace document revision (idempotent per lineage and revision) and
    read the job's status with the proposal prefill payload once finished.
    Proposals are advisory: the status handler builds MACHINE_PROPOSED
    prefill copies for the editor; nothing is ever written into a saved
    document revision.

Relationships:
    Reuses the ``exam_answer_key_enrichment_jobs`` queue through
    ``source_kind='workspace'`` (no second queue); the worker branch lives in
    ``application.curated_apps.handlers.exam_answer_key_enrichment_jobs``.
    Document access goes through the versioned Mina filer head exactly like
    ``exam_workspace_documents``.
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    enqueue_workspace_enrichment_job,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.domain.curated_apps.exam_workspace.answer_key_view import (
    WorkspaceAnswerKeyProposalsPayload,
    answer_key_item_views,
    apply_proposal_to_item,
    proposal_from_record,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamItem,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault import VaultFile
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import (
    ExamAnswerKeyEnrichmentJobRepositoryProtocol,
    ExamAnswerKeyProposedOverlayRepositoryProtocol,
)
from skriptoteket.protocols.exam_workspace import ExamWorkspaceContainerCodecProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol

NOT_ELIGIBLE_MESSAGE = (
    "Inga facitförslag kan skapas: dokumentet saknar frågor utan facit "
    "eller så är funktionen avstängd."
)

_DEFAULT_FAILURE_MESSAGE = "Facitförslaget kunde inte hämtas just nu. Försök igen senare."

_FAILURE_MESSAGES: dict[str, str] = {
    "daily_token_lease_exhausted": (
        "Dagens AI-budget för facitförslag är förbrukad. Försök igen i morgon."
    ),
    "llm_output_invalid": "Facitförslaget kunde inte tolkas. Komplettera facit manuellt.",
    "workspace_no_enrichable_items": "Dokumentet har inga frågor som saknar facit.",
    "workspace_document_revision_stale": (
        "Dokumentet har ändrats sedan förslaget begärdes. Begär förslag igen."
    ),
    "workspace_container_invalid": "Den sparade dokumentversionen kunde inte läsas.",
}


class ExamWorkspaceEnrichmentState(StrEnum):
    """Teacher-facing state of the enrichment lane for one head revision."""

    NOT_REQUESTED = "not_requested"
    NOT_ELIGIBLE = "not_eligible"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ExamWorkspaceAnswerKeyProposalItem(BaseModel):
    """One advisory prefill proposal with its provider candidate lineage."""

    model_config = ConfigDict(frozen=True)

    item_id: str
    proposed_item: NativeExamItem
    provider_profile_id: str
    model: str
    prompt_template_version: str


class ExamWorkspaceEnrichmentStatusResponse(BaseModel):
    """Status plus advisory proposals for one document head revision."""

    model_config = ConfigDict(frozen=True)

    lineage_id: UUID
    document_revision: int = Field(ge=1)
    state: ExamWorkspaceEnrichmentState
    message: str | None = None
    proposals: tuple[ExamWorkspaceAnswerKeyProposalItem, ...] = ()


def _document_not_found(lineage_id: UUID) -> DomainError:
    return DomainError(
        code=ErrorCode.NOT_FOUND,
        message="Provdokumentet finns inte.",
        details={"lineage_id": str(lineage_id)},
    )


class EnqueueExamWorkspaceEnrichmentHandler:
    """Enqueue one workspace-lane enrichment job for a document revision."""

    def __init__(
        self,
        *,
        enrichment_jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        enrichment_enabled: bool,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._enrichment_jobs = enrichment_jobs
        self._enrichment_enabled = enrichment_enabled
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator

    async def handle(self, *, actor: User, document: NativeExamDocument) -> bool:
        """Insert one queued workspace job; report whether one was inserted.

        Idempotent per (lineage, revision): an existing job for the same
        revision leaves the queue untouched and returns False. Disabled
        enrichment or a document without unkeyed keyed items also returns
        False without touching the queue.
        """

        if not self._enrichment_enabled:
            return False
        if not answer_key_item_views(document):
            return False
        now = self._clock.now()
        async with self._uow:
            existing = await self._enrichment_jobs.get_by_workspace_revision(
                owner_user_id=actor.id,
                workspace_lineage_id=document.document_id,
                workspace_document_revision=document.revision,
            )
            if existing is not None:
                return False
            await self._enrichment_jobs.create(
                job=enqueue_workspace_enrichment_job(
                    job_id=self._id_generator.new_uuid(),
                    owner_user_id=actor.id,
                    input_filename=document.title[:255],
                    workspace_lineage_id=document.document_id,
                    workspace_document_revision=document.revision,
                    now=now,
                )
            )
        return True


class GetExamWorkspaceEnrichmentStatusHandler:
    """Read enrichment status and advisory proposals for the head revision."""

    def __init__(
        self,
        *,
        vault_files: VaultFileRepositoryProtocol,
        enrichment_jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        proposed_overlays: ExamAnswerKeyProposedOverlayRepositoryProtocol,
        store: ExamWorkspaceDocumentStore,
        codec: ExamWorkspaceContainerCodecProtocol,
    ) -> None:
        self._vault_files = vault_files
        self._enrichment_jobs = enrichment_jobs
        self._proposed_overlays = proposed_overlays
        self._store = store
        self._codec = codec

    async def handle(
        self, *, actor: User, lineage_id: UUID
    ) -> ExamWorkspaceEnrichmentStatusResponse:
        head = await self._vault_files.get_document_head(
            user_id=actor.id, document_lineage_id=lineage_id
        )
        if head is None or head.document_version is None:
            raise _document_not_found(lineage_id)
        revision = head.document_version
        job = await self._enrichment_jobs.get_by_workspace_revision(
            owner_user_id=actor.id,
            workspace_lineage_id=lineage_id,
            workspace_document_revision=revision,
        )
        if job is None:
            return ExamWorkspaceEnrichmentStatusResponse(
                lineage_id=lineage_id,
                document_revision=revision,
                state=ExamWorkspaceEnrichmentState.NOT_REQUESTED,
            )
        if job.status is ExamAnswerKeyEnrichmentJobStatus.QUEUED:
            return self._status_only(lineage_id, revision, ExamWorkspaceEnrichmentState.QUEUED)
        if job.status is ExamAnswerKeyEnrichmentJobStatus.RUNNING:
            return self._status_only(lineage_id, revision, ExamWorkspaceEnrichmentState.RUNNING)
        if job.status is ExamAnswerKeyEnrichmentJobStatus.FAILED:
            return ExamWorkspaceEnrichmentStatusResponse(
                lineage_id=lineage_id,
                document_revision=revision,
                state=ExamWorkspaceEnrichmentState.FAILED,
                message=_FAILURE_MESSAGES.get(job.last_error or "", _DEFAULT_FAILURE_MESSAGE),
            )
        return await self._succeeded_response(
            actor=actor, lineage_id=lineage_id, revision=revision, job=job, head_vault_file=head
        )

    def _status_only(
        self,
        lineage_id: UUID,
        revision: int,
        state: ExamWorkspaceEnrichmentState,
    ) -> ExamWorkspaceEnrichmentStatusResponse:
        return ExamWorkspaceEnrichmentStatusResponse(
            lineage_id=lineage_id,
            document_revision=revision,
            state=state,
        )

    async def _succeeded_response(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        revision: int,
        job: ExamAnswerKeyEnrichmentJob,
        head_vault_file: VaultFile,
    ) -> ExamWorkspaceEnrichmentStatusResponse:
        overlay = await self._proposed_overlays.get_by_enrichment_job_id(enrichment_job_id=job.id)
        if overlay is None:
            return ExamWorkspaceEnrichmentStatusResponse(
                lineage_id=lineage_id,
                document_revision=revision,
                state=ExamWorkspaceEnrichmentState.FAILED,
                message=_DEFAULT_FAILURE_MESSAGE,
            )
        try:
            payload = WorkspaceAnswerKeyProposalsPayload.model_validate(overlay.overlay_json)
        except ValidationError:
            return ExamWorkspaceEnrichmentStatusResponse(
                lineage_id=lineage_id,
                document_revision=revision,
                state=ExamWorkspaceEnrichmentState.FAILED,
                message=_DEFAULT_FAILURE_MESSAGE,
            )
        content = await self._store.load_version(actor=actor, vault_file=head_vault_file)
        container = self._codec.parse(content=content)
        proposals: list[ExamWorkspaceAnswerKeyProposalItem] = []
        for record in payload.items:
            try:
                item = container.document.item_by_id(record.item_id)
                proposed_item = apply_proposal_to_item(item, proposal_from_record(record))
            except (DomainError, ValidationError):
                continue
            proposals.append(
                ExamWorkspaceAnswerKeyProposalItem(
                    item_id=record.item_id,
                    proposed_item=proposed_item,
                    provider_profile_id=record.provider_profile_id,
                    model=record.model,
                    prompt_template_version=record.prompt_template_version,
                )
            )
        return ExamWorkspaceEnrichmentStatusResponse(
            lineage_id=lineage_id,
            document_revision=revision,
            state=ExamWorkspaceEnrichmentState.SUCCEEDED,
            proposals=tuple(proposals),
        )
