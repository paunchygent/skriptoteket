"""One save model: every editor command stores an undo step and overwrites the exam file.

The undo-step store also writes the stored document to the exam file in Mina filer in the
same transaction, so the file always holds what the teacher sees. A position move sets the
editor's snapshot without storing a step and writes that snapshot the same way.
Relationships: file, index and usage writes run through ``ExamWorkspaceDocumentStore``;
the cursor and the editing tab's lease guard each write while the server assigns each file revision.
"""

from uuid import UUID

from skriptoteket.application.curated_apps.exam_workspace_history import (
    ExamWorkspaceUndoStepResponse,
    MoveExamWorkspaceHistoryPositionRequest,
    StoreExamWorkspaceUndoStepRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_edit_lease import (
    require_edit_lease,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_editor_content import (
    prepare_editor_content,
    refuse_placeholder_changes,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.clock import ClockProtocol
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
        clock: ClockProtocol,
    ) -> None:
        self._vault_files = vault_files
        self._codec = codec
        self._store = store
        self._jobs = jobs
        self._ids = id_generator
        self._clock = clock

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
            history_head = await self._store.ensure_history_head(actor=actor, lineage_id=lineage_id)
            require_edit_lease(
                lease=await self._vault_files.get_history_lease(
                    user_id=actor.id, document_lineage_id=lineage_id
                ),
                tab_id=request.tab_id,
                now=self._clock.now(),
            )
            if history_head.cursor != request.expected_cursor:
                raise DomainError(
                    code=ErrorCode.CONFLICT,
                    message="Dokumentet har ändrats sedan det öppnades.",
                    details={
                        "expected_cursor": str(request.expected_cursor),
                        "current_cursor": str(history_head.cursor),
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
                history_head.current_step_id
                if request.after_step_id is None
                else request.after_step_id
            )
            step_id = self._ids.new_uuid()
            await self._store.write_step_file(
                actor=actor,
                lineage_id=lineage_id,
                content=content,
                document=document,
                version=version,
            )
            stored = self._codec.parse(content=content)
            history = await self._store.append_history_step(
                actor=actor,
                lineage_id=lineage_id,
                head=history_head,
                step_id=step_id,
                document=document,
                assets_by_id=dict(stored.assets_by_id),
                notes=stored.notes,
                after_step_id=after,
            )
            return ExamWorkspaceUndoStepResponse(document=document, history=history)

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
            history_head = await self._store.ensure_history_head(actor=actor, lineage_id=lineage_id)
            require_edit_lease(
                lease=await self._vault_files.get_history_lease(
                    user_id=actor.id, document_lineage_id=lineage_id
                ),
                tab_id=request.tab_id,
                now=self._clock.now(),
            )
            if history_head.cursor != request.expected_cursor:
                raise DomainError(
                    code=ErrorCode.CONFLICT,
                    message="Dokumentet har ändrats sedan det öppnades.",
                    details={
                        "expected_cursor": str(request.expected_cursor),
                        "current_cursor": str(history_head.cursor),
                    },
                )
            snapshot = await self._store.get_history_step_document(
                actor=actor, lineage_id=lineage_id, step_id=request.step_id
            )
            assert head.document_version is not None
            version = head.document_version + 1
            document = snapshot.model_copy(update={"revision": version})
            _head, saved, content = await prepare_editor_content(
                actor=actor,
                lineage_id=lineage_id,
                document=document,
                vault_files=self._vault_files,
                codec=self._codec,
                store=self._store,
            )
            refuse_placeholder_changes(job=job, base=saved.document, saved=document)
            await self._store.write_step_file(
                actor=actor,
                lineage_id=lineage_id,
                content=content,
                document=document,
                version=version,
            )
            history = await self._store.move_history_position(
                actor=actor,
                lineage_id=lineage_id,
                head=history_head,
                step_id=request.step_id,
                new_cursor=self._ids.new_uuid(),
            )
            return ExamWorkspaceUndoStepResponse(document=document, history=history)
