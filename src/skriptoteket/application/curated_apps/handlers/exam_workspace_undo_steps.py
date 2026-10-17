"""Store one editor undo step through the same cursor guard for every command."""

from uuid import UUID

from skriptoteket.application.curated_apps.exam_workspace_history import (
    ExamWorkspaceHistoryStep,
    ExamWorkspaceUndoStepResponse,
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
            document = request.document.model_copy(update={"revision": head.document_version})
            _head, saved, content = await prepare_editor_content(
                actor=actor,
                lineage_id=lineage_id,
                document=document,
                vault_files=self._vault_files,
                codec=self._codec,
                store=self._store,
            )
            refuse_placeholder_changes(job=job, base=saved.document, saved=document)
            steps = history.steps
            if request.after_step_id is not None:
                ids = (history.baseline.step_id, *(step.step_id for step in steps))
                if request.after_step_id not in ids:
                    raise DomainError(
                        code=ErrorCode.CONFLICT, message="Ångrasteget finns inte längre."
                    )
                steps = steps[: ids.index(request.after_step_id)]
            step_id = self._ids.new_uuid()
            steps = (*steps, ExamWorkspaceHistoryStep(step_id=step_id, content=content))[-10:]
            history = history.model_copy(
                update={"cursor": step_id, "current_step_id": step_id, "steps": steps}
            )
            await self._store.put_history(actor=actor, lineage_id=lineage_id, history=history)
            return ExamWorkspaceUndoStepResponse(
                document=document, history=history_response(history)
            )
