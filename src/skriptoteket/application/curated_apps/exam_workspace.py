"""Exam workspace application DTOs (ST-SKRIPT-39-04 walking skeleton)."""

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKeySuggestion,
    NativeExamDocument,
    NativeExamItem,
    NativeExamItemKind,
)


class ExamWorkspaceDocumentSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    lineage_id: UUID
    version: int = Field(ge=1)
    vault_file_id: UUID
    name: str
    saved_at: datetime


class ExamWorkspaceConversionUnit(BaseModel):
    """Items conversion last wrote for one question or question-less review item.

    ``converting`` items are placeholders that only the unit's later batch may change;
    ``ready`` items are converted and editable.
    """

    model_config = ConfigDict(frozen=True)

    unit_id: str
    question: bool
    state: Literal["converting", "ready"]
    item_ids: tuple[str, ...]


class ExamWorkspaceConversionStatus(BaseModel):
    """Owner-visible status of one background DOCX import.

    ``document_revision`` is the latest revision conversion saved, absent until the
    first batch is ready; ``units`` lets the editor merge each new revision into
    unsaved teacher edits.
    """

    model_config = ConfigDict(frozen=True)

    job_id: UUID
    lineage_id: UUID
    state: Literal["queued", "running", "succeeded", "failed"]
    error_message: str | None
    document_revision: int | None
    questions_total: int
    questions_done: int
    units: tuple[ExamWorkspaceConversionUnit, ...]


class ExamWorkspaceDocumentResponse(BaseModel):
    """One document revision, with the DOCX import that created its lineage.

    ``conversion`` is read under the same lock as the document, so its units name exactly
    the placeholders this revision still holds; it is None for a lineage no import created.
    """

    model_config = ConfigDict(frozen=True)

    document: NativeExamDocument
    summary: ExamWorkspaceDocumentSummary
    notes: tuple[str, ...] = ()
    conversion: ExamWorkspaceConversionStatus | None


class ExamWorkspaceDocumentListResponse(BaseModel):
    """The actor's workspace documents, one head version per lineage."""

    model_config = ConfigDict(frozen=True)

    documents: tuple[ExamWorkspaceDocumentSummary, ...] = ()


class SaveExamWorkspaceDocumentRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    expected_revision: int = Field(ge=1)
    document: NativeExamDocument


class ExamWorkspaceEnrichmentState(StrEnum):
    """Teacher-facing state of one answer-key suggestion job."""

    NOT_ELIGIBLE = "not_eligible"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class RequestExamWorkspaceAnswerKeySuggestionsRequest(BaseModel):
    """Editor-sent content for one suggestion request (TASK-SKRIPT-39-04-07).

    ``document`` is the exam exactly as the editor shows it, saved or not.
    With ``item_id`` the request covers that one question, with or without
    a key; without it, it covers every keyed-kind question without a key.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    document: NativeExamDocument
    item_id: str | None = None


class ExamWorkspaceAnswerKeySuggestionItem(BaseModel):
    """One AI suggestion that arrived for one question."""

    model_config = ConfigDict(frozen=True)

    item_id: str
    suggestion: NativeAnswerKeySuggestion


class ExamWorkspaceAnswerKeySuggestionsResponse(BaseModel):
    """Status of one suggestion job, plus its suggestions once finished."""

    model_config = ConfigDict(frozen=True)

    job_id: UUID | None = None
    lineage_id: UUID
    state: ExamWorkspaceEnrichmentState
    message: str | None = None
    suggestions: tuple[ExamWorkspaceAnswerKeySuggestionItem, ...] = ()


class RetryExamWorkspaceItemRequest(BaseModel):
    """Editor-sent content for one single-question reconversion (TASK-SKRIPT-39-05-09 D1).

    ``document`` is the exam exactly as the editor shows it; the saved head revision is the
    authority for the question's original source, so the draft's own copy of the item is
    never read as source. ``kind`` is the type the teacher keeps or chooses.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    document: NativeExamDocument
    item_id: str
    kind: NativeExamItemKind


class ExamWorkspaceItemRetryResponse(BaseModel):
    """The one item a retry replaces its question with; everything else stays put."""

    model_config = ConfigDict(frozen=True)

    lineage_id: UUID
    item: NativeExamItem


class ExamWorkspaceExportTarget(StrEnum):
    QTI = "qti"
    PDF = "pdf"
    DOCX = "docx"


class ExamWorkspaceExportFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    filename: str
    media_type: str
    content: bytes
