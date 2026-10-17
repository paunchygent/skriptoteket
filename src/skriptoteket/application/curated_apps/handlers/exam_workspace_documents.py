"""Exam workspace document handlers: DOCX import, conversion status, reopen, list, and save.

Import queues one teacher DOCX as a background conversion. Each exam has one
saved vault file and a separate bounded editor history. Reopen shows the current
editor document (the latest autosave or Spara); save overwrites the file guarded
by ``expected_revision``. Converting
placeholders retain their content and position until conversion completes.
Persistence and storage accounting live in ``exam_workspace_document_store``.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
    ExamWorkspaceConversionJobView,
)
from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceConversionStatus,
    ExamWorkspaceConversionUnit,
    ExamWorkspaceDocumentListResponse,
    ExamWorkspaceDocumentResponse,
    ExamWorkspaceDocumentSummary,
    SaveExamWorkspaceDocumentRequest,
)
from skriptoteket.application.curated_apps.exam_workspace_history import (
    ExamWorkspaceHistoryDocumentResponse,
    ExamWorkspaceHistoryResponse,
    ExamWorkspaceHistoryState,
    SaveAsExamWorkspaceDocumentRequest,
    history_response,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_merge import (
    ConversionProgress,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    EXAM_WORKSPACE_SOURCE_ARTIFACT_PREFIX,
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_editor_content import (
    prepare_editor_content,
    refuse_placeholder_changes,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.exam_course_catalog import (
    load_exam_course_catalog,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.input_files import sanitize_input_filename
from skriptoteket.domain.scripting.vault import VaultFile
from skriptoteket.domain.scripting.vault_names import rename_vault_filename
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import ExamAnswerKeyEnrichmentJobRepositoryProtocol
from skriptoteket.protocols.exam_workspace import (
    ExamWorkspaceContainerCodecProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol


def _document_not_found(lineage_id: UUID) -> DomainError:
    return DomainError(
        code=ErrorCode.NOT_FOUND,
        message="Provdokumentet finns inte.",
        details={"lineage_id": str(lineage_id)},
    )


def _summary(vault_file: VaultFile) -> ExamWorkspaceDocumentSummary:
    assert vault_file.document_lineage_id is not None
    assert vault_file.document_version is not None
    assert vault_file.document_saved_at is not None
    return ExamWorkspaceDocumentSummary(
        lineage_id=vault_file.document_lineage_id,
        version=vault_file.document_version,
        vault_file_id=vault_file.id,
        name=vault_file.name,
        saved_at=vault_file.document_saved_at,
    )


class ImportExamWorkspaceDocumentHandler:
    """Import one teacher DOCX into a new exam workspace document."""

    def __init__(
        self,
        *,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        settings: Settings,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._jobs = jobs
        self._uow = uow
        self._clock = clock
        self._settings = settings
        self._id_generator = id_generator

    async def handle(
        self, *, actor: User, filename: str, content: bytes, course_key: str | None
    ) -> ExamWorkspaceConversionStatus:
        safe_name = sanitize_input_filename(input_filename=filename)
        if not safe_name.lower().endswith(".docx"):
            raise validation_error("Välj en .docx-fil.", details={"filename": safe_name})
        if not content:
            raise validation_error("Filen saknar innehåll.")
        if len(content) > self._settings.VAULT_MAX_FILE_BYTES:
            raise validation_error("Word-dokumentet är större än maxstorleken för Mina filer.")

        selected_course_key = (course_key or "").strip() or None
        if selected_course_key is not None:
            if len(selected_course_key) > 64:
                raise validation_error(
                    "Kurskoden får vara högst 64 tecken.", details={"field": "course_key"}
                )
            if not any(
                course.key == selected_course_key for course in load_exam_course_catalog().courses
            ):
                raise validation_error(
                    "Välj en kurs ur kurslistan.", details={"field": "course_key"}
                )

        document_id = self._id_generator.new_uuid()
        now = self._clock.now()
        async with self._uow:
            job = await self._jobs.create(
                job=ExamAnswerKeyEnrichmentJob(
                    id=self._id_generator.new_uuid(),
                    source_kind=ExamAnswerKeySourceKind.DOCX_IMPORT,
                    owner_user_id=actor.id,
                    status=ExamAnswerKeyEnrichmentJobStatus.QUEUED,
                    input_filename=safe_name,
                    source_docx=content,
                    workspace_lineage_id=document_id,
                    workspace_document_revision=1,
                    workspace_course_key=selected_course_key,
                    available_at=now,
                    created_at=now,
                    updated_at=now,
                )
            )
        return conversion_status(
            ExamWorkspaceConversionJobView.model_validate(job, from_attributes=True)
        )


def conversion_status(job: ExamWorkspaceConversionJobView) -> ExamWorkspaceConversionStatus:
    assert job.workspace_lineage_id is not None
    progress = ConversionProgress.model_validate(job.conversion_progress or {})
    return ExamWorkspaceConversionStatus(
        job_id=job.id,
        lineage_id=job.workspace_lineage_id,
        state=job.status.value,
        error_message=job.last_error
        if job.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
        else None,
        document_revision=progress.revision,
        questions_total=progress.questions_total,
        questions_done=progress.questions_done,
        units=tuple(
            ExamWorkspaceConversionUnit(
                unit_id=unit.unit_id,
                question=unit.question,
                state=unit.state.value,
                item_ids=unit.item_ids,
            )
            for unit in progress.units
            if unit.digest is not None
        ),
    )


class GetExamWorkspaceConversionStatusHandler:
    """Read one actor-owned background conversion without exposing source bytes."""

    def __init__(self, *, jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol) -> None:
        self._jobs = jobs

    async def handle(self, *, actor: User, job_id: UUID) -> ExamWorkspaceConversionStatus:
        job = await self._jobs.get_conversion_view(job_id=job_id)
        if (
            job is None
            or job.owner_user_id != actor.id
            or job.source_kind is not ExamAnswerKeySourceKind.DOCX_IMPORT
        ):
            raise DomainError(code=ErrorCode.NOT_FOUND, message="Konverteringen finns inte.")
        return conversion_status(job)


class GetExamWorkspaceDocumentHandler:
    """Reopen the current editor document without changing retained undo steps."""

    def __init__(
        self,
        *,
        vault_files: VaultFileRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> None:
        self._vault_files = vault_files
        self._codec = codec
        self._store = store
        self._jobs = jobs
        self._uow = uow

    async def handle(self, *, actor: User, lineage_id: UUID) -> ExamWorkspaceDocumentResponse:
        # The job lock holds conversion back, so the head matches the conversion's units.
        async with self._store.transaction(user_id=actor.id, lineage_id=lineage_id):
            job = await self._jobs.lock_conversion_view_by_lineage(
                owner_user_id=actor.id, workspace_lineage_id=lineage_id
            )
            await self._vault_files.lock_document_lineage(
                user_id=actor.id, document_lineage_id=lineage_id
            )
            head = await self._vault_files.get_document_head(
                user_id=actor.id, document_lineage_id=lineage_id
            )
            if head is None:
                raise _document_not_found(lineage_id)
            content = await self._store.load(actor=actor, vault_file=head)
            history = await self._store.get_history(actor=actor, lineage_id=lineage_id)
            assert history is not None
        container = self._codec.parse(content=content)
        if (
            container.document.document_id != lineage_id
            or container.document.revision != head.document_version
        ):
            raise validation_error(
                "Den sparade dokumentversionen är skadad.",
                details={"lineage_id": str(lineage_id)},
            )
        current = next(
            (step for step in history.steps if step.step_id == history.current_step_id), None
        )
        latest = container if current is None else self._codec.parse(content=current.content)
        document = latest.document.model_copy(update={"revision": head.document_version})
        return ExamWorkspaceDocumentResponse(
            document=document,
            summary=_summary(head),
            history_cursor=history.cursor,
            notes=container.notes,
            conversion=None if job is None else conversion_status(job),
        )


class ListExamWorkspaceDocumentsHandler:
    """List the actor's workspace documents as head-version summaries."""

    def __init__(self, *, vault_files: VaultFileRepositoryProtocol) -> None:
        self._vault_files = vault_files

    async def handle(self, *, actor: User) -> ExamWorkspaceDocumentListResponse:
        heads = await self._vault_files.list_document_heads(
            user_id=actor.id,
            source_artifact_prefix=f"{EXAM_WORKSPACE_SOURCE_ARTIFACT_PREFIX}:",
        )
        return ExamWorkspaceDocumentListResponse(documents=tuple(_summary(head) for head in heads))


class SaveExamWorkspaceDocumentHandler:
    """Save, autosave and copy an editor document without creating vault revisions."""

    def __init__(
        self,
        *,
        vault_files: VaultFileRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
        id_generator: IdGeneratorProtocol,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
    ) -> None:
        self._vault_files = vault_files
        self._codec = codec
        self._store = store
        self._id_generator = id_generator
        self._jobs = jobs

    async def handle(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        request: SaveExamWorkspaceDocumentRequest,
    ) -> ExamWorkspaceDocumentResponse:
        async with self._store.transaction(user_id=actor.id, lineage_id=lineage_id):
            await self._jobs.lock_conversion_view_by_lineage(
                owner_user_id=actor.id, workspace_lineage_id=lineage_id
            )
            await self._vault_files.lock_document_lineage(
                user_id=actor.id, document_lineage_id=lineage_id
            )
            return await self._save(actor=actor, lineage_id=lineage_id, request=request)

    async def _save(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        request: SaveExamWorkspaceDocumentRequest,
    ) -> ExamWorkspaceDocumentResponse:
        head = await self._vault_files.get_document_head(
            user_id=actor.id, document_lineage_id=lineage_id
        )
        if head is None:
            raise _document_not_found(lineage_id)
        if head.document_version != request.expected_revision:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message="Dokumentet har ändrats sedan det öppnades.",
                details={
                    "expected_revision": request.expected_revision,
                    "current_revision": head.document_version,
                },
            )
        document = request.document
        if document.document_id != lineage_id:
            raise validation_error(
                "Dokumentets identitet matchar inte adressen.",
                details={"lineage_id": str(lineage_id)},
            )
        if document.revision != request.expected_revision + 1:
            raise validation_error(
                "Dokumentversionen måste öka med exakt ett vid sparande.",
                details={
                    "expected_revision": request.expected_revision,
                    "document_revision": document.revision,
                },
            )

        head, head_container, container_bytes = await prepare_editor_content(
            actor=actor,
            lineage_id=lineage_id,
            document=document,
            vault_files=self._vault_files,
            codec=self._codec,
            store=self._store,
        )
        job = await self._jobs.lock_conversion_view_by_lineage(
            owner_user_id=actor.id, workspace_lineage_id=lineage_id
        )
        refuse_placeholder_changes(job=job, base=head_container.document, saved=document)
        vault_file = await self._store.save(
            actor=actor,
            file_id=self._id_generator.new_uuid(),
            name=head.name,
            content=container_bytes,
            lineage_id=lineage_id,
            version=document.revision,
            expected_revision=request.expected_revision,
        )
        history = await self._store.get_history(actor=actor, lineage_id=lineage_id)
        assert history is not None
        return ExamWorkspaceDocumentResponse(
            document=document,
            history_cursor=history.cursor,
            summary=_summary(vault_file),
            notes=head_container.notes,
            conversion=None if job is None else conversion_status(job),
        )

    async def _history(self, *, actor: User, lineage_id: UUID) -> ExamWorkspaceHistoryState:
        head = await self._vault_files.get_document_head(
            user_id=actor.id, document_lineage_id=lineage_id
        )
        if head is None:
            raise _document_not_found(lineage_id)
        history = await self._store.get_history(actor=actor, lineage_id=lineage_id)
        assert history is not None
        return history

    async def history(self, *, actor: User, lineage_id: UUID) -> ExamWorkspaceHistoryResponse:
        return history_response(await self._history(actor=actor, lineage_id=lineage_id))

    async def history_step(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        step_id: UUID,
    ) -> ExamWorkspaceHistoryDocumentResponse:
        history = await self._history(actor=actor, lineage_id=lineage_id)
        step = next(
            (step for step in (history.baseline, *history.steps) if step.step_id == step_id), None
        )
        if step is None:
            raise DomainError(code=ErrorCode.NOT_FOUND, message="Ångrasteget finns inte.")
        head = await self._vault_files.get_document_head(
            user_id=actor.id, document_lineage_id=lineage_id
        )
        if head is None:
            raise _document_not_found(lineage_id)
        document = self._codec.parse(content=step.content).document.model_copy(
            update={"revision": head.document_version}
        )
        return ExamWorkspaceHistoryDocumentResponse(step_id=step_id, document=document)

    async def save_as(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        request: SaveAsExamWorkspaceDocumentRequest,
    ) -> ExamWorkspaceDocumentResponse:
        name = rename_vault_filename(stem=request.name, extension=".provdokument.zip")
        async with self._store.transaction(user_id=actor.id, lineage_id=lineage_id):
            await self._vault_files.lock_owner_renames(user_id=actor.id)
            await self._vault_files.lock_document_lineage(
                user_id=actor.id, document_lineage_id=lineage_id
            )
            if await self._vault_files.name_in_use(
                user_id=actor.id, name=name, exclude_lineage_id=None, exclude_file_id=None
            ):
                raise validation_error(
                    "Namnet används redan av en annan fil.",
                    details={"code": "vault_name_in_use", "name": name},
                )
            _head, saved, content = await prepare_editor_content(
                actor=actor,
                lineage_id=lineage_id,
                document=request.document,
                vault_files=self._vault_files,
                codec=self._codec,
                store=self._store,
            )
            current = self._codec.parse(content=content)
            copy_id = self._id_generator.new_uuid()
            copied = current.document.model_copy(update={"document_id": copy_id, "revision": 1})
            content = self._codec.build(content=current.model_copy(update={"document": copied}))
            vault_file = await self._store.save(
                actor=actor,
                file_id=self._id_generator.new_uuid(),
                name=name,
                content=content,
                lineage_id=copy_id,
                version=1,
            )
            return ExamWorkspaceDocumentResponse(
                document=copied,
                summary=_summary(vault_file),
                history_cursor=copy_id,
                notes=saved.notes,
                conversion=None,
            )
