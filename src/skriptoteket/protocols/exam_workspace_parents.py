"""Application boundary for teacher parent commands."""

from typing import Protocol
from uuid import UUID

from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceDocumentResponse
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
from skriptoteket.domain.identity.models import User


class ExamWorkspaceParentsHandlerProtocol(Protocol):
    async def create_parent(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        request: CreateExamParentRequest,
    ) -> ExamWorkspaceDocumentResponse: ...

    async def add_child(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        parent_id: str,
        request: AddExamChildRequest,
    ) -> ExamWorkspaceDocumentResponse: ...

    async def group_items(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        request: GroupExamItemsRequest,
    ) -> ExamWorkspaceCreatedPartResponse: ...

    async def move_item(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        request: MoveExamItemRequest,
    ) -> ExamWorkspaceDocumentResponse: ...

    async def create_empty_part(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        request: CreateEmptyExamPartRequest,
    ) -> ExamWorkspaceCreatedPartResponse: ...

    async def delete_parent(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        parent_id: str,
        request: ParentCommandRequest,
    ) -> ExamWorkspaceDeleteResponse: ...

    async def delete_parent_with_children(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        parent_id: str,
        request: ParentCommandRequest,
    ) -> ExamWorkspaceDeleteResponse: ...

    async def delete_child(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        parent_id: str,
        item_id: str,
        request: ParentCommandRequest,
    ) -> ExamWorkspaceDeleteResponse: ...

    async def reorder_children(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        parent_id: str,
        request: ReorderExamChildrenRequest,
    ) -> ExamWorkspaceDocumentResponse: ...
