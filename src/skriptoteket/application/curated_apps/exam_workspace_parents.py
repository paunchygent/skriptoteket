"""Parent command requests. Positions are zero-based insertion indexes."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceDocumentResponse
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import NativeParagraph
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem


class ParentCommandRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    expected_cursor: UUID
    tab_id: UUID
    """The editing tab's id; the server refuses a command from a tab without the lease."""


class ExamWorkspaceDeleteResponse(ExamWorkspaceDocumentResponse):
    """One undoable deletion; names a removed instruction for an inline notice."""

    removed_parent_id: str | None


class ExamWorkspaceCreatedPartResponse(ExamWorkspaceDocumentResponse):
    """One undoable part creation; names the new part the UI opens in its editor (G4)."""

    created_parent_id: str


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


class GroupExamItemsRequest(ParentCommandRequest):
    """Marked standalone questions become one new part (G2, G10)."""

    item_ids: tuple[str, ...] = Field(min_length=1)


class MoveExamItemRequest(ParentCommandRequest):
    """Move one question into a part, or to None for "Ingen del (fristående)" (G3, R3, R4)."""

    item_id: str
    target_parent_id: str | None


class CreateEmptyExamPartRequest(ParentCommandRequest):
    """Insert a part with an empty instruction at a top-level position (G9)."""

    position: int = Field(ge=0, description="Zero-based index among top-level questions and parts.")
