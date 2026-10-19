"""Application seam shared by editor autosaves and native document commands."""

from typing import Protocol
from uuid import UUID

from skriptoteket.application.curated_apps.exam_workspace_history import (
    ExamWorkspaceUndoStepResponse,
    MoveExamWorkspaceHistoryPositionRequest,
    StoreExamWorkspaceUndoStepRequest,
)
from skriptoteket.domain.identity.models import User


class StoreExamWorkspaceUndoStepHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        request: StoreExamWorkspaceUndoStepRequest,
    ) -> ExamWorkspaceUndoStepResponse: ...

    async def move_to_step(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        request: MoveExamWorkspaceHistoryPositionRequest,
    ) -> ExamWorkspaceUndoStepResponse: ...
