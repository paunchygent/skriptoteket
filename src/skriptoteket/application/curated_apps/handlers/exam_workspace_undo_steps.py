"""One save model: every editor command stores an undo step and overwrites the exam file.

The undo-step store also writes the stored document to the exam file in Mina filer in the
same transaction, so the file always holds what the teacher sees. A position move sets the
editor's snapshot without storing a step and writes that snapshot the same way.
Relationships: file, index and usage writes run through ``ExamWorkspaceDocumentStore``;
the cursor stays the only guard while the server assigns each file revision.
"""

from uuid import UUID

from skriptoteket.application.curated_apps.exam_workspace_history import (
    MAX_RETAINED_UNDO_STEPS,
    ExamWorkspaceHistoryStep,
    ExamWorkspaceUndoStepResponse,
    MoveExamWorkspaceHistoryPositionRequest,
    StoreExamWorkspaceUndoStepRequest,
    history_response,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_editor_content import (
    prepare_editor_content,
    refuse_placeholder_changes,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.exam_answer_key import ExamAnswerKeyEnrichmentJobRepositoryProtocol
from skriptoteket.protocols.exam_workspace import ExamWorkspaceContainerCodecProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol


class StoreExamWorkspaceUndoStepHandler:
    def __init__(
        self,
        *,
        vault_files: VaultFileRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._vault_files = vault_files
        self._codec = codec
        self._store = store
        self._jobs = jobs
        self._ids = id_generator

    async def handle(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        request: StoreExamWorkspaceUndoStepRequest,
    ) -> ExamWorkspaceUndoStepResponse:
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
                raise DomainError(code=ErrorCode.NOT_FOUND, message="Provdokumentet finns inte.")
            history = await self._store.get_history(actor=actor, lineage_id=lineage_id)
            assert history is not None
            if history.cursor != request.expected_cursor:
                raise DomainError(
                    code=ErrorCode.CONFLICT,
                    message="Dokumentet har ändrats sedan det öppnades.",
                    details={
                        "expected_cursor": str(request.expected_cursor),
                        "current_cursor": str(history.cursor),
                    },
                )
            assert head.document_version is not None
            version = head.document_version + 1
            document = request.document.model_copy(update={"revision": version})
            _head, saved, content = await prepare_editor_content(
                actor=actor,
                lineage_id=lineage_id,
                document=document,
                vault_files=self._vault_files,
                codec=self._codec,
                store=self._store,
            )
            refuse_placeholder_changes(job=job, base=saved.document, saved=document)
            # A new step follows the snapshot the editor stands on and drops its redo steps;
            # the server's commands send no position and follow the current one.
            after = (
                history.current_step_id if request.after_step_id is None else request.after_step_id
            )
            ids = (history.baseline.step_id, *(step.step_id for step in history.steps))
            if after not in ids:
                raise DomainError(code=ErrorCode.CONFLICT, message="Ångrasteget finns inte längre.")
            steps = history.steps[: ids.index(after)]
            step_id = self._ids.new_uuid()
            steps = (*steps, ExamWorkspaceHistoryStep(step_id=step_id, content=content))[
                -MAX_RETAINED_UNDO_STEPS:
            ]
            history = history.model_copy(
                update={"cursor": step_id, "current_step_id": step_id, "steps": steps}
            )
            await self._store.write_step_file(
                actor=actor,
                lineage_id=lineage_id,
                content=content,
                document=document,
                version=version,
            )
            await self._store.put_history(actor=actor, lineage_id=lineage_id, history=history)
            return ExamWorkspaceUndoStepResponse(
                document=document, history=history_response(history)
            )

    async def move_to_step(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        request: MoveExamWorkspaceHistoryPositionRequest,
    ) -> ExamWorkspaceUndoStepResponse:
        """Move the editor to a retained snapshot and write it to the exam file, no new step."""
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
                raise DomainError(code=ErrorCode.NOT_FOUND, message="Provdokumentet finns inte.")
            history = await self._store.get_history(actor=actor, lineage_id=lineage_id)
            assert history is not None
            if history.cursor != request.expected_cursor:
                raise DomainError(
                    code=ErrorCode.CONFLICT,
                    message="Dokumentet har ändrats sedan det öppnades.",
                    details={
                        "expected_cursor": str(request.expected_cursor),
                        "current_cursor": str(history.cursor),
                    },
                )
            step = next(
                (
                    snapshot
                    for snapshot in (history.baseline, *history.steps)
                    if snapshot.step_id == request.step_id
                ),
                None,
            )
            if step is None:
                raise DomainError(code=ErrorCode.NOT_FOUND, message="Ångrasteget finns inte.")
            assert head.document_version is not None
            version = head.document_version + 1
            document = self._codec.parse(content=step.content).document.model_copy(
                update={"revision": version}
            )
            _head, saved, content = await prepare_editor_content(
                actor=actor,
                lineage_id=lineage_id,
                document=document,
                vault_files=self._vault_files,
                codec=self._codec,
                store=self._store,
            )
            refuse_placeholder_changes(job=job, base=saved.document, saved=document)
            history = history.model_copy(
                update={"cursor": self._ids.new_uuid(), "current_step_id": step.step_id}
            )
            await self._store.write_step_file(
                actor=actor,
                lineage_id=lineage_id,
                content=content,
                document=document,
                version=version,
            )
            await self._store.put_history(actor=actor, lineage_id=lineage_id, history=history)
            return ExamWorkspaceUndoStepResponse(
                document=document, history=history_response(history)
            )
