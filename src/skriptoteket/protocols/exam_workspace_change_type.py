"""Typed boundary for a teacher's question-type command."""

from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceDocumentResponse
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    ITEM_ID_PATTERN,
    NativeExamItemKind,
)
from skriptoteket.domain.identity.models import User


class ChangeExamWorkspaceItemTypeRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    item_id: str = Field(pattern=ITEM_ID_PATTERN)
    target_kind: NativeExamItemKind
    expected_revision: int = Field(ge=1)
    expected_cursor: UUID


class ChangeExamWorkspaceItemTypeResponse(ExamWorkspaceDocumentResponse):
    dropped_content: tuple[str, ...]


class ChangeExamWorkspaceItemTypeHandlerProtocol(Protocol):
    async def handle(
        self, *, actor: User, lineage_id: UUID, request: ChangeExamWorkspaceItemTypeRequest
    ) -> ChangeExamWorkspaceItemTypeResponse: ...
