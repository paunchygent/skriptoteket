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

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.application.curated_apps.exam_workspace_export_blockers import (
    NativeDocumentWithExportBlockers,
)
from skriptoteket.application.curated_apps.exam_workspace_parents import NewParentChild
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import NativeParagraph
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    ITEM_ID_PATTERN,
    NativeExamItemKind,
)


class PublicExamDocumentCommandResponse(NativeDocumentWithExportBlockers):
    """The transformed document plus the export gate's verdict on it."""

    model_config = ConfigDict(frozen=True)


class PublicExamBlankResponse(PublicExamDocumentCommandResponse):
    """The fresh blank exam a guest starts from."""


class PublicExamWorkspaceQtiImportResponse(BaseModel):
    """One parsed QTI package for a guest: the document plus its picture bytes.

    Asset bytes travel as base64 JSON strings, the typed response-side
    counterpart to the ``asset:<id>`` multipart parts the guest export routes
    read: the browser decodes each value back to bytes and keeps them beside
    its draft. Nothing is stored server-side.
    """

    model_config = ConfigDict(frozen=True, ser_json_bytes="base64", val_json_bytes="base64")

    document: NativeExamDocument
    assets_by_id: dict[str, bytes] = {}
    notes: tuple[str, ...] = ()


class PublicExamDocumentDeleteResponse(PublicExamDocumentCommandResponse):
    """One guest deletion; names a removed instruction for an inline notice."""

    removed_parent_id: str | None


class PublicExamChangeTypeResponse(PublicExamDocumentCommandResponse):
    """One guest type change; names what the change removed."""

    dropped_content: tuple[str, ...]


class PublicExamCreatedPartResponse(PublicExamDocumentCommandResponse):
    """One guest part creation; names the new part the UI opens in its editor."""

    created_parent_id: str


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


class PublicGroupExamItemsRequest(PublicExamWorkspaceDocumentRequest):
    """Marked standalone questions become one new part (G2, G10)."""

    item_ids: tuple[str, ...] = Field(min_length=1)


class PublicCreateEmptyExamPartRequest(PublicExamWorkspaceDocumentRequest):
    """Insert a part with an empty instruction at a top-level position (G9)."""

    position: int = Field(ge=0, description="Zero-based index among top-level questions and parts.")


class PublicMoveExamItemRequest(PublicExamWorkspaceDocumentRequest):
    """Move one question into a part, or to None for "Ingen del (fristående)" (G3, R3, R4)."""

    item_id: str
    target_parent_id: str | None


class PublicChangeExamItemTypeRequest(PublicExamWorkspaceDocumentRequest):
    item_id: str = Field(pattern=ITEM_ID_PATTERN)
    target_kind: NativeExamItemKind
