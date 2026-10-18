"""Boundary models for the stateless public exam workspace commands (B2b).

Purpose:
    Carry the whole browser-held document plus the signed-in command fields
    minus ``expected_cursor``/``expected_revision``: a guest has no server-held
    cursor or revision to compare against.

Relationships:
    - Reuses the signed-in parent-command item and field shapes field-for-field.
    - Responses mirror ``ExamWorkspaceDocumentResponse``'s computed
      ``export_blockers`` without its server-held lineage fields.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from skriptoteket.application.curated_apps.exam_workspace_parents import NewParentChild
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import NativeParagraph
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    NativeExportBlocker,
    native_export_blockers,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    ITEM_ID_PATTERN,
    NativeExamItemKind,
)


class PublicExamDocumentCommandResponse(BaseModel):
    """The transformed document plus the export gate's verdict on it."""

    model_config = ConfigDict(frozen=True)

    document: NativeExamDocument

    @computed_field  # type: ignore[prop-decorator]
    @property
    def export_blockers(self) -> tuple[NativeExportBlocker, ...]:
        return native_export_blockers(self.document)


class PublicExamBlankResponse(PublicExamDocumentCommandResponse):
    """The fresh blank exam a guest starts from."""


class PublicExamDocumentDeleteResponse(PublicExamDocumentCommandResponse):
    """One guest deletion; names a removed instruction for an inline notice."""

    removed_parent_id: str | None


class PublicExamChangeTypeResponse(PublicExamDocumentCommandResponse):
    """One guest type change; names what the change removed."""

    dropped_content: tuple[str, ...]


class PublicExamWorkspaceDocumentRequest(BaseModel):
    """The browser-held document every guest command carries."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    document: NativeExamDocument


class PublicCreateExamParentRequest(PublicExamWorkspaceDocumentRequest):
    instruction: tuple[NativeParagraph, ...] = Field(min_length=1)
    child: NewParentChild
    position: int = Field(
        ge=0,
        description="Zero-based insertion index among standalone questions and whole parents.",
    )


class PublicAddExamChildRequest(PublicExamWorkspaceDocumentRequest):
    child: NewParentChild
    position: int = Field(ge=0, description="Zero-based insertion index within the parent.")


class PublicReorderExamChildrenRequest(PublicExamWorkspaceDocumentRequest):
    item_ids: tuple[str, ...] = Field(min_length=1)


class PublicDeleteExamParentRequest(PublicExamWorkspaceDocumentRequest):
    mode: Literal["keep_questions", "with_questions"]


class PublicChangeExamItemTypeRequest(PublicExamWorkspaceDocumentRequest):
    item_id: str = Field(pattern=ITEM_ID_PATTERN)
    target_kind: NativeExamItemKind
