"""Exam workspace document handlers: conversion status, reopen, history, and copy.

Reopen shows the current editor document (the latest stored undo step); every edit
stores an undo step, which also overwrites the file. Converting placeholders retain
their content and position until conversion completes. Persistence and storage
accounting live in ``exam_workspace_document_store``.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
    ExamWorkspaceConversionJobView,
)
from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceConversionStatus,
    ExamWorkspaceConversionUnit,
    ExamWorkspaceDocumentResponse,
    ExamWorkspaceDocumentSummary,
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
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_editor_content import (
    prepare_editor_content,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    with_kept_answer_key_retry,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault import VaultFile
from skriptoteket.domain.scripting.vault_names import rename_vault_filename
from skriptoteket.protocols.exam_answer_key import ExamAnswerKeyEnrichmentJobRepositoryProtocol
from skriptoteket.protocols.exam_index import ExamIndexRepositoryProtocol
from skriptoteket.protocols.exam_workspace import (
    ExamWorkspaceContainerCodecProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol


def document_not_found(lineage_id: UUID) -> DomainError:
    return DomainError(
        code=ErrorCode.NOT_FOUND,
        message="Provdokumentet finns inte.",
        details={"lineage_id": str(lineage_id)},
    )


def document_summary(
    vault_file: VaultFile, document: NativeExamDocument
) -> ExamWorkspaceDocumentSummary:
    assert vault_file.document_lineage_id is not None
    assert vault_file.document_version is not None
    assert vault_file.document_saved_at is not None
    return ExamWorkspaceDocumentSummary(
        lineage_id=vault_file.document_lineage_id,
        version=vault_file.document_version,
        vault_file_id=vault_file.id,
        name=vault_file.name,
        saved_at=vault_file.document_saved_at,
        title=document.title,
        course_key=None if document.header.course is None else document.header.course.key,
    )


def conversion_status(
    job: ExamWorkspaceConversionJobView,
    *,
    summary: ExamWorkspaceDocumentSummary | None = None,
) -> ExamWorkspaceConversionStatus:
    assert job.workspace_lineage_id is not None
    progress = ConversionProgress.model_validate(job.conversion_progress or {})
    return ExamWorkspaceConversionStatus(
        job_id=job.id,
        lineage_id=job.workspace_lineage_id,
        state=job.status.value,
        error_message=job.last_error
        if job.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
        else None,
        ai_limit=job.ai_limit,
        document_revision=progress.revision,
        questions_total=progress.questions_total,
        questions_done=progress.questions_done,
        questions_received=progress.questions_received,
        phase=job.conversion_phase,
        phase_started_at=job.conversion_phase_started_at,
        summary=summary,
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

    def __init__(
        self,
        *,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        index: ExamIndexRepositoryProtocol,
    ) -> None:
        self._jobs = jobs
        self._index = index

    async def handle(self, *, actor: User, job_id: UUID) -> ExamWorkspaceConversionStatus:
        job = await self._jobs.get_conversion_view(job_id=job_id)
        if (
            job is None
            or job.owner_user_id != actor.id
            or job.source_kind
            not in {
                ExamAnswerKeySourceKind.DOCX_IMPORT,
                ExamAnswerKeySourceKind.DIGIEXAM_IMPORT,
            }
        ):
            raise DomainError(code=ErrorCode.NOT_FOUND, message="Konverteringen finns inte.")
        assert job.workspace_lineage_id is not None
        exam = await self._index.get(owner_user_id=actor.id, lineage_id=job.workspace_lineage_id)
        summary = (
            None
            if exam is None
            else ExamWorkspaceDocumentSummary(
                lineage_id=exam.lineage_id,
                version=exam.version,
                vault_file_id=exam.head_vault_file_id,
                name=exam.name,
                saved_at=exam.saved_at,
                title=exam.title,
                course_key=exam.course_key,
            )
        )
        return conversion_status(job, summary=summary)


class GetExamWorkspaceDocumentHandler:
    """Reopen the current editor document without changing retained undo steps.

    The reopened document keeps the saved head's answer-key retries, so a reload
    never offers a spent retry again (TASK-SKRIPT-40-04-26 D4).
    """

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
                raise document_not_found(lineage_id)
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
        current = history.current_step()
        latest = self._codec.parse(content=current.content)
        # Reopening installs the current undo step's document, so it keeps the saved
        # head's answer-key retries and cannot offer a spent retry again
        # (TASK-SKRIPT-40-04-26 D4).
        opened = with_kept_answer_key_retry(latest.document, container.document)
        document = opened.model_copy(update={"revision": head.document_version})
        return ExamWorkspaceDocumentResponse(
            document=document,
            saved_document=container.document,
            summary=document_summary(head, container.document),
            history_cursor=history.cursor,
            notes=container.notes,
            conversion=None if job is None else conversion_status(job),
        )


class SaveExamWorkspaceDocumentHandler:
    """Read history and copy an editor document; every edit stores an undo step instead."""

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

    async def _history(self, *, actor: User, lineage_id: UUID) -> ExamWorkspaceHistoryState:
        head = await self._vault_files.get_document_head(
            user_id=actor.id, document_lineage_id=lineage_id
        )
        if head is None:
            raise document_not_found(lineage_id)
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
            raise document_not_found(lineage_id)
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
                saved_document=copied,
                summary=document_summary(vault_file, copied),
                history_cursor=copy_id,
                notes=saved.notes,
                conversion=None,
            )
