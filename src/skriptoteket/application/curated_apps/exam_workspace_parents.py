"""Parent command requests. Positions are zero-based insertion indexes."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceDocumentResponse
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import NativeParagraph
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem


class ParentCommandRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    expected_cursor: UUID


class ExamWorkspaceDeleteResponse(ExamWorkspaceDocumentResponse):
    """One undoable deletion; names a removed instruction for an inline notice."""

    removed_parent_id: str | None


class NewParentChild(NativeExamItem):
    """Item content; identity and order are assigned by the server."""

    item_id: str = Field(default="item_001", pattern=r"^item_[0-9]{3,4}$")
    sequence: int = Field(default=1, ge=1)


class CreateExamParentRequest(ParentCommandRequest):
    instruction: tuple[NativeParagraph, ...] = Field(min_length=1)
    child: NewParentChild
    position: int = Field(
        ge=0,
        description="Zero-based insertion index among standalone questions and whole parents.",
    )


class AddExamChildRequest(ParentCommandRequest):
    child: NewParentChild
    position: int = Field(ge=0, description="Zero-based insertion index within the parent.")


class ReorderExamChildrenRequest(ParentCommandRequest):
    item_ids: tuple[str, ...] = Field(min_length=1)
