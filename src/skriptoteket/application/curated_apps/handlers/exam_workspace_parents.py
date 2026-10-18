"""Apply one parent command to the newest editor step without saving the exam file."""

from collections.abc import Callable
from uuid import UUID

from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceDocumentResponse
from skriptoteket.application.curated_apps.exam_workspace_history import (
    StoreExamWorkspaceUndoStepRequest,
)
from skriptoteket.application.curated_apps.exam_workspace_parents import (
    AddExamChildRequest,
    CreateEmptyExamPartRequest,
    CreateExamParentRequest,
    ExamWorkspaceCreatedPartResponse,
    ExamWorkspaceDeleteResponse,
    GroupExamItemsRequest,
    MoveExamItemRequest,
    ParentCommandRequest,
    ReorderExamChildrenRequest,
)
from skriptoteket.domain.curated_apps.exam_workspace import native_exam_parent_commands as commands
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.exam_workspace import (
    GetExamWorkspaceDocumentHandlerProtocol,
)
from skriptoteket.protocols.exam_workspace_history import (
    StoreExamWorkspaceUndoStepHandlerProtocol,
)


class ExamWorkspaceParentsHandler:
    def __init__(
        self,
        *,
        reader: GetExamWorkspaceDocumentHandlerProtocol,
        undo_steps: StoreExamWorkspaceUndoStepHandlerProtocol,
    ) -> None:
        self._reader = reader
        self._undo_steps = undo_steps

    async def _apply(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        expected_cursor: UUID,
        operation: Callable[[NativeExamDocument], NativeExamDocument],
    ) -> ExamWorkspaceDocumentResponse:
        current = await self._reader.handle(actor=actor, lineage_id=lineage_id)
        if current.history_cursor != expected_cursor:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message="Dokumentet har ändrats sedan det öppnades.",
                details={
                    "expected_cursor": str(expected_cursor),
                    "current_cursor": str(current.history_cursor),
                },
            )
        document = operation(current.document)
        # The shared seam checks the cursor atomically, including changes after this read.
        # Omit the branch position: commands always append to the newest undo step.
        stored = await self._undo_steps.handle(
            actor=actor,
            lineage_id=lineage_id,
            request=StoreExamWorkspaceUndoStepRequest(
                expected_cursor=expected_cursor, document=document
            ),
        )
        return current.model_copy(
            update={"document": stored.document, "history_cursor": stored.history.cursor}
        )

    async def create_parent(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        request: CreateExamParentRequest,
    ) -> ExamWorkspaceDocumentResponse:
        return await self._apply(
            actor=actor,
            lineage_id=lineage_id,
            expected_cursor=request.expected_cursor,
            operation=lambda document: commands.create_parent(
                document,
                instruction=request.instruction,
                child=request.child,
                position=request.position,
            ),
        )

    async def add_child(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        parent_id: str,
        request: AddExamChildRequest,
    ) -> ExamWorkspaceDocumentResponse:
        return await self._apply(
            actor=actor,
            lineage_id=lineage_id,
            expected_cursor=request.expected_cursor,
            operation=lambda document: commands.add_child(
                document, parent_id=parent_id, child=request.child, position=request.position
            ),
        )

    async def group_items(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        request: GroupExamItemsRequest,
    ) -> ExamWorkspaceCreatedPartResponse:
        created_parent_id = ""

        def operation(document: NativeExamDocument) -> NativeExamDocument:
            nonlocal created_parent_id
            result, created_parent_id = commands.group_items(document, item_ids=request.item_ids)
            return result

        response = await self._apply(
            actor=actor,
            lineage_id=lineage_id,
            expected_cursor=request.expected_cursor,
            operation=operation,
        )
        return ExamWorkspaceCreatedPartResponse(
            **response.model_dump(), created_parent_id=created_parent_id
        )

    async def move_item(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        request: MoveExamItemRequest,
    ) -> ExamWorkspaceDocumentResponse:
        return await self._apply(
            actor=actor,
            lineage_id=lineage_id,
            expected_cursor=request.expected_cursor,
            operation=lambda document: commands.move_item(
                document,
                item_id=request.item_id,
                target_parent_id=request.target_parent_id,
            ),
        )

    async def create_empty_part(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        request: CreateEmptyExamPartRequest,
    ) -> ExamWorkspaceCreatedPartResponse:
        created_parent_id = ""

        def operation(document: NativeExamDocument) -> NativeExamDocument:
            nonlocal created_parent_id
            result, created_parent_id = commands.create_empty_part(
                document, position=request.position
            )
            return result

        response = await self._apply(
            actor=actor,
            lineage_id=lineage_id,
            expected_cursor=request.expected_cursor,
            operation=operation,
        )
        return ExamWorkspaceCreatedPartResponse(
            **response.model_dump(), created_parent_id=created_parent_id
        )

    async def _delete(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        parent_id: str,
        request: ParentCommandRequest,
        operation: Callable[[NativeExamDocument], NativeExamDocument],
    ) -> ExamWorkspaceDeleteResponse:
        result = await self._apply(
            actor=actor,
            lineage_id=lineage_id,
            expected_cursor=request.expected_cursor,
            operation=operation,
        )
        removed_parent_id = (
            None if any(p.parent_id == parent_id for p in result.document.parents) else parent_id
        )
        return ExamWorkspaceDeleteResponse(
            **result.model_dump(), removed_parent_id=removed_parent_id
        )

    async def delete_parent(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        parent_id: str,
        request: ParentCommandRequest,
    ) -> ExamWorkspaceDeleteResponse:
        return await self._delete(
            actor=actor,
            lineage_id=lineage_id,
            parent_id=parent_id,
            request=request,
            operation=lambda document: commands.delete_parent(document, parent_id=parent_id),
        )

    async def delete_parent_with_children(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        parent_id: str,
        request: ParentCommandRequest,
    ) -> ExamWorkspaceDeleteResponse:
        return await self._delete(
            actor=actor,
            lineage_id=lineage_id,
            parent_id=parent_id,
            request=request,
            operation=lambda document: commands.delete_parent_with_children(
                document, parent_id=parent_id
            ),
        )

    async def delete_child(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        parent_id: str,
        item_id: str,
        request: ParentCommandRequest,
    ) -> ExamWorkspaceDeleteResponse:
        return await self._delete(
            actor=actor,
            lineage_id=lineage_id,
            parent_id=parent_id,
            request=request,
            operation=lambda document: commands.delete_child(
                document, parent_id=parent_id, item_id=item_id
            ),
        )

    async def reorder_children(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        parent_id: str,
        request: ReorderExamChildrenRequest,
    ) -> ExamWorkspaceDocumentResponse:
        return await self._apply(
            actor=actor,
            lineage_id=lineage_id,
            expected_cursor=request.expected_cursor,
            operation=lambda document: commands.reorder_children(
                document, parent_id=parent_id, item_ids=request.item_ids
            ),
        )
