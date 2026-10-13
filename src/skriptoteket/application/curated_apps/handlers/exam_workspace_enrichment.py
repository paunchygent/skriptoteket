"""Exam workspace answer-key suggestions: request and status handlers.

Purpose:
    Start one AI answer-key suggestion job on the questions exactly as the
    editor shows them (TASK-SKRIPT-39-04-07) and read the job's status with
    one suggestion per question that got a valid answer. A request sends
    either one named question, with or without a key, or every keyed-kind
    question without a key; it works while the editor has unsaved changes
    because the job runs on the sent content, never on the saved head.

Relationships:
    Reuses the ``exam_answer_key_enrichment_jobs`` queue through
    ``source_kind='workspace'`` (no second queue); the worker branch lives in
    ``exam_answer_key_enrichment_workspace_lane``. Suggestions arrive as
    data for the editor to write onto its questions; nothing here writes a
    saved document revision.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationError

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
    enqueue_workspace_enrichment_job,
)
from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceAnswerKeySuggestionItem,
    ExamWorkspaceAnswerKeySuggestionsResponse,
    ExamWorkspaceEnrichmentState,
    RequestExamWorkspaceAnswerKeySuggestionsRequest,
)
from skriptoteket.domain.curated_apps.exam_workspace.answer_key_view import (
    AnswerKeyItemView,
    answer_key_item_view,
    answer_key_item_views,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import (
    ExamAnswerKeyEnrichmentJobRepositoryProtocol,
)
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
    "workspace_request_missing": _DEFAULT_FAILURE_MESSAGE,
    "workspace_request_invalid": _DEFAULT_FAILURE_MESSAGE,
}


def _document_not_found(lineage_id: UUID) -> DomainError:
    return DomainError(
        code=ErrorCode.NOT_FOUND,
        message="Provdokumentet finns inte.",
        details={"lineage_id": str(lineage_id)},
    )


class WorkspaceAnswerKeyRequestPayload(BaseModel):
    """The answer-key views one workspace suggestion job runs on."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    views: tuple[AnswerKeyItemView, ...]


class WorkspaceAnswerKeySuggestionsPayload(BaseModel):
    """The suggestions one finished workspace suggestion job produced."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    suggestions: tuple[ExamWorkspaceAnswerKeySuggestionItem, ...]


class RequestExamWorkspaceAnswerKeySuggestionsHandler:
    """Enqueue one suggestion job on editor-sent content."""

    def __init__(
        self,
        *,
        enrichment_jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        enrichment_enabled: bool,
        vault_files: VaultFileRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._enrichment_jobs = enrichment_jobs
        self._enrichment_enabled = enrichment_enabled
        self._vault_files = vault_files
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        request: RequestExamWorkspaceAnswerKeySuggestionsRequest,
    ) -> ExamWorkspaceAnswerKeySuggestionsResponse:
        document = request.document
        if document.document_id != lineage_id:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Dokumentet hör till en annan provrad.",
                details={"lineage_id": str(lineage_id)},
            )
        head = await self._vault_files.get_document_head(
            user_id=actor.id, document_lineage_id=lineage_id
        )
        if head is None:
            raise _document_not_found(lineage_id)
        views = self._selected_views(request)
        if not self._enrichment_enabled or not views:
            return ExamWorkspaceAnswerKeySuggestionsResponse(
                lineage_id=lineage_id,
                state=ExamWorkspaceEnrichmentState.NOT_ELIGIBLE,
                message=NOT_ELIGIBLE_MESSAGE,
            )
        job_id = self._id_generator.new_uuid()
        payload = WorkspaceAnswerKeyRequestPayload(views=views)
        async with self._uow:
            await self._enrichment_jobs.create(
                job=enqueue_workspace_enrichment_job(
                    job_id=job_id,
                    owner_user_id=actor.id,
                    input_filename=document.title[:255],
                    workspace_lineage_id=lineage_id,
                    workspace_request_json=payload.model_dump(mode="json"),
                    now=self._clock.now(),
                )
            )
        return ExamWorkspaceAnswerKeySuggestionsResponse(
            job_id=job_id,
            lineage_id=lineage_id,
            state=ExamWorkspaceEnrichmentState.QUEUED,
        )

    @staticmethod
    def _selected_views(
        request: RequestExamWorkspaceAnswerKeySuggestionsRequest,
    ) -> tuple[AnswerKeyItemView, ...]:
        document = request.document
        if request.item_id is None:
            return answer_key_item_views(document)
        item = document.item_by_id(request.item_id)
        try:
            return (answer_key_item_view(item, document.parent_of(item.item_id)),)
        except ValueError:
            return ()


class GetExamWorkspaceAnswerKeySuggestionsStatusHandler:
    """Read one suggestion job's status and, once finished, its suggestions."""

    def __init__(
        self,
        *,
        enrichment_jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
    ) -> None:
        self._enrichment_jobs = enrichment_jobs

    async def handle(
        self, *, actor: User, lineage_id: UUID, job_id: UUID
    ) -> ExamWorkspaceAnswerKeySuggestionsResponse:
        job = await self._enrichment_jobs.get_by_id(job_id=job_id)
        if (
            job is None
            or job.owner_user_id != actor.id
            or job.source_kind is not ExamAnswerKeySourceKind.WORKSPACE
            or job.workspace_lineage_id != lineage_id
        ):
            raise DomainError(
                code=ErrorCode.NOT_FOUND,
                message="Facitförslaget finns inte.",
                details={"job_id": str(job_id)},
            )
        if job.status is ExamAnswerKeyEnrichmentJobStatus.QUEUED:
            return self._status(lineage_id, job_id, ExamWorkspaceEnrichmentState.QUEUED)
        if job.status is ExamAnswerKeyEnrichmentJobStatus.RUNNING:
            return self._status(lineage_id, job_id, ExamWorkspaceEnrichmentState.RUNNING)
        if job.status is ExamAnswerKeyEnrichmentJobStatus.FAILED:
            return ExamWorkspaceAnswerKeySuggestionsResponse(
                job_id=job_id,
                lineage_id=lineage_id,
                state=ExamWorkspaceEnrichmentState.FAILED,
                message=_FAILURE_MESSAGES.get(job.last_error or "", _DEFAULT_FAILURE_MESSAGE),
            )
        if job.workspace_suggestions_json is None:
            return ExamWorkspaceAnswerKeySuggestionsResponse(
                job_id=job_id,
                lineage_id=lineage_id,
                state=ExamWorkspaceEnrichmentState.FAILED,
                message=_DEFAULT_FAILURE_MESSAGE,
            )
        try:
            payload = WorkspaceAnswerKeySuggestionsPayload.model_validate(
                job.workspace_suggestions_json
            )
        except ValidationError:
            return ExamWorkspaceAnswerKeySuggestionsResponse(
                job_id=job_id,
                lineage_id=lineage_id,
                state=ExamWorkspaceEnrichmentState.FAILED,
                message=_DEFAULT_FAILURE_MESSAGE,
            )
        return ExamWorkspaceAnswerKeySuggestionsResponse(
            job_id=job_id,
            lineage_id=lineage_id,
            state=ExamWorkspaceEnrichmentState.SUCCEEDED,
            suggestions=payload.suggestions,
        )

    @staticmethod
    def _status(
        lineage_id: UUID, job_id: UUID, state: ExamWorkspaceEnrichmentState
    ) -> ExamWorkspaceAnswerKeySuggestionsResponse:
        return ExamWorkspaceAnswerKeySuggestionsResponse(
            job_id=job_id,
            lineage_id=lineage_id,
            state=state,
        )
