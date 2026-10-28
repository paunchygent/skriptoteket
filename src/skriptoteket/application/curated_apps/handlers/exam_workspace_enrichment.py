"""Exam workspace answer-key suggestions: request, status and resume handlers.

Purpose:
    Start one AI answer-key suggestion job on the questions exactly as the
    editor shows them (TASK-SKRIPT-39-04-07) and read the job's status with
    one suggestion per question that got a valid answer. A request sends
    either one named question whose key is not source-provided, or every
    keyed-kind question without a key. It works while the editor has unsaved
    changes because the job runs on the sent content, never on the saved head.
    Each job records the saved version the editor's copy stood on, so an
    exam opened again finds the newest job for its current saved version,
    and a request repeating a queued or running job's exact content gets
    that job back instead of a second model call (TASK-SKRIPT-39-04-09).
    A single-question request on a question whose one answer-key retry is
    spent is refused before any job lookup (TASK-SKRIPT-40-04-26 D4).

Relationships:
    Reuses the ``exam_answer_key_enrichment_jobs`` queue through
    ``source_kind='workspace'`` (no second queue); the worker branch lives in
    ``exam_answer_key_enrichment_workspace_lane``. Suggestions arrive as
    data for the editor to write onto its questions; nothing here writes a
    saved document revision.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, JsonValue, ValidationError

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
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
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeAnswerKeyRetry,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.llm_door import AiDailyLimit, ai_limit_note, ai_try_again_note
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import (
    ExamAnswerKeyEnrichmentJobRepositoryProtocol,
    ExamWorkspaceSuggestionJobQueryProtocol,
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
    "llm_output_invalid": "Facitförslaget kunde inte tolkas. Komplettera facit manuellt.",
    "workspace_no_enrichable_items": "Dokumentet har inga frågor som saknar facit.",
    "workspace_request_missing": _DEFAULT_FAILURE_MESSAGE,
    "workspace_request_invalid": _DEFAULT_FAILURE_MESSAGE,
    "ai_door_busy": ai_try_again_note(),
}


def _failure_message(job: ExamAnswerKeyEnrichmentJob) -> str:
    """The teacher message for a failed job: the limit note from the job's limit, else
    the note for its last error (a busy door asks to try again)."""
    if job.ai_limit is not None:
        return ai_limit_note(job.ai_limit)
    return _FAILURE_MESSAGES.get(job.last_error or "", _DEFAULT_FAILURE_MESSAGE)


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
        suggestion_jobs: ExamWorkspaceSuggestionJobQueryProtocol,
        enrichment_enabled: bool,
        vault_files: VaultFileRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._enrichment_jobs = enrichment_jobs
        self._suggestion_jobs = suggestion_jobs
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
        if request.item_id is not None and (
            document.item_by_id(request.item_id).answer_key_retry is NativeAnswerKeyRetry.USED
        ):
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message="Frågan har redan fått sitt nya facitförslag.",
                details={"item_id": request.item_id},
            )
        views = self._selected_views(request)
        if not self._enrichment_enabled or not views:
            return ExamWorkspaceAnswerKeySuggestionsResponse(
                lineage_id=lineage_id,
                state=ExamWorkspaceEnrichmentState.NOT_ELIGIBLE,
                message=NOT_ELIGIBLE_MESSAGE,
            )
        request_json = WorkspaceAnswerKeyRequestPayload(views=views).model_dump(mode="json")
        async with self._uow:
            # Lookup and enqueue are one decision per saved version: a
            # concurrent equal request waits here and then finds this job.
            await self._suggestion_jobs.lock_workspace_requests(
                owner_user_id=actor.id,
                workspace_lineage_id=lineage_id,
                workspace_document_revision=document.revision,
            )
            running = await self._suggestion_jobs.get_active_workspace_job(
                owner_user_id=actor.id,
                workspace_lineage_id=lineage_id,
                workspace_document_revision=document.revision,
                workspace_request_json=request_json,
            )
            if running is not None:
                # The same questions on the same saved version are already
                # being answered: hand that job back instead of a second model call.
                return suggestions_response_for_job(running, lineage_id=lineage_id)
            job_id = self._id_generator.new_uuid()
            await self._enrichment_jobs.create(
                job=enqueue_workspace_enrichment_job(
                    job_id=job_id,
                    owner_user_id=actor.id,
                    input_filename=document.title[:255],
                    workspace_lineage_id=lineage_id,
                    workspace_document_revision=document.revision,
                    workspace_request_json=request_json,
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
        if item.answer_key.origin is NativeAnswerKeyOrigin.SOURCE_PROVIDED:
            return ()
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
        return suggestions_response_for_job(job, lineage_id=lineage_id)


class FindExamWorkspaceAnswerKeySuggestionsHandler:
    """Find the newest suggestion job requested on an exam's current saved version."""

    def __init__(
        self,
        *,
        suggestion_jobs: ExamWorkspaceSuggestionJobQueryProtocol,
        vault_files: VaultFileRepositoryProtocol,
    ) -> None:
        self._suggestion_jobs = suggestion_jobs
        self._vault_files = vault_files

    async def handle(
        self, *, actor: User, lineage_id: UUID, document_revision: int
    ) -> ExamWorkspaceAnswerKeySuggestionsResponse | None:
        head = await self._vault_files.get_document_head(
            user_id=actor.id, document_lineage_id=lineage_id
        )
        if head is None:
            raise _document_not_found(lineage_id)
        if head.document_version != document_revision:
            # The editor's copy is not the current saved version: a job
            # requested on it belongs to an older version and never applies.
            return None
        job = await self._suggestion_jobs.get_latest_workspace_job(
            owner_user_id=actor.id,
            workspace_lineage_id=lineage_id,
            workspace_document_revision=document_revision,
        )
        if job is None:
            return None
        return suggestions_response_for_job(job, lineage_id=lineage_id)


def suggestions_response_for_job(
    job: ExamAnswerKeyEnrichmentJob, *, lineage_id: UUID
) -> ExamWorkspaceAnswerKeySuggestionsResponse:
    """Report one suggestion job's state and, once finished, its suggestions."""

    if job.status is ExamAnswerKeyEnrichmentJobStatus.QUEUED:
        return _status(lineage_id, job.id, ExamWorkspaceEnrichmentState.QUEUED, job.ai_limit)
    if job.status is ExamAnswerKeyEnrichmentJobStatus.RUNNING:
        return _status(lineage_id, job.id, ExamWorkspaceEnrichmentState.RUNNING, job.ai_limit)
    payload = _stored_suggestions(job.workspace_suggestions_json)
    if job.status is ExamAnswerKeyEnrichmentJobStatus.FAILED:
        # A failed job still delivers every suggestion it produced before
        # the failure, alongside the truthful failure message.
        return ExamWorkspaceAnswerKeySuggestionsResponse(
            job_id=job.id,
            lineage_id=lineage_id,
            state=ExamWorkspaceEnrichmentState.FAILED,
            ai_limit=job.ai_limit,
            message=_failure_message(job),
            suggestions=payload.suggestions if payload is not None else (),
        )
    if payload is None:
        return ExamWorkspaceAnswerKeySuggestionsResponse(
            job_id=job.id,
            lineage_id=lineage_id,
            state=ExamWorkspaceEnrichmentState.FAILED,
            ai_limit=job.ai_limit,
            message=_DEFAULT_FAILURE_MESSAGE,
        )
    return ExamWorkspaceAnswerKeySuggestionsResponse(
        job_id=job.id,
        lineage_id=lineage_id,
        state=ExamWorkspaceEnrichmentState.SUCCEEDED,
        ai_limit=job.ai_limit,
        suggestions=payload.suggestions,
    )


def _stored_suggestions(
    suggestions_json: dict[str, JsonValue] | None,
) -> WorkspaceAnswerKeySuggestionsPayload | None:
    if suggestions_json is None:
        return None
    try:
        return WorkspaceAnswerKeySuggestionsPayload.model_validate(suggestions_json)
    except ValidationError:
        return None


def _status(
    lineage_id: UUID,
    job_id: UUID,
    state: ExamWorkspaceEnrichmentState,
    ai_limit: AiDailyLimit | None,
) -> ExamWorkspaceAnswerKeySuggestionsResponse:
    return ExamWorkspaceAnswerKeySuggestionsResponse(
        job_id=job_id,
        lineage_id=lineage_id,
        state=state,
        ai_limit=ai_limit,
    )
