"""Retype the selected working copy and append exactly one server undo step."""

from uuid import UUID

from skriptoteket.application.curated_apps.exam_workspace_history import (
    StoreExamWorkspaceUndoStepRequest,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_change_type import change_item_type
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.exam_workspace import GetExamWorkspaceDocumentHandlerProtocol
from skriptoteket.protocols.exam_workspace_change_type import (
    ChangeExamWorkspaceItemTypeRequest,
    ChangeExamWorkspaceItemTypeResponse,
)
from skriptoteket.protocols.exam_workspace_history import StoreExamWorkspaceUndoStepHandlerProtocol


class ChangeExamWorkspaceItemTypeHandler:
    def __init__(
        self,
        *,
        reader: GetExamWorkspaceDocumentHandlerProtocol,
        undo_steps: StoreExamWorkspaceUndoStepHandlerProtocol,
    ) -> None:
        self._reader = reader
        self._undo_steps = undo_steps

    async def handle(
        self, *, actor: User, lineage_id: UUID, request: ChangeExamWorkspaceItemTypeRequest
    ) -> ChangeExamWorkspaceItemTypeResponse:
        current = await self._reader.handle(actor=actor, lineage_id=lineage_id)
        if (
            current.document.revision != request.expected_revision
            or current.history_cursor != request.expected_cursor
        ):
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message="Dokumentet har ändrats sedan det öppnades.",
                details={
                    "expected_revision": request.expected_revision,
                    "current_revision": current.document.revision,
                    "expected_cursor": str(request.expected_cursor),
                    "current_cursor": str(current.history_cursor),
                },
            )
        result = change_item_type(
            current.document, item_id=request.item_id, target_kind=request.target_kind
        )
        # The existing seam checks the cursor again atomically with the autosave.
        stored = await self._undo_steps.handle(
            actor=actor,
            lineage_id=lineage_id,
            request=StoreExamWorkspaceUndoStepRequest(
                expected_cursor=request.expected_cursor, document=result.document
            ),
        )
        return ChangeExamWorkspaceItemTypeResponse(
            **{
                **current.model_dump(),
                "document": stored.document,
                "history_cursor": stored.history.cursor,
            },
            dropped_content=result.dropped_content,
        )
