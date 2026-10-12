"""Exam workspace application DTOs (ST-SKRIPT-39-04 walking skeleton)."""

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamItem,
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
    rejected_proposal_item_ids: tuple[str, ...] = ()


class ExamWorkspaceEnrichmentState(StrEnum):
    """Teacher-facing state of the enrichment lane for one head revision."""

    NOT_REQUESTED = "not_requested"
    NOT_ELIGIBLE = "not_eligible"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ExamWorkspaceAnswerKeyProposalItem(BaseModel):
    """One advisory prefill proposal with its provider candidate lineage."""

    model_config = ConfigDict(frozen=True)

    item_id: str
    proposed_item: NativeExamItem
    provider_profile_id: str
    model: str
    prompt_template_version: str


class ExamWorkspaceEnrichmentStatusResponse(BaseModel):
    """Status plus advisory proposals for one document head revision."""

    model_config = ConfigDict(frozen=True)

    lineage_id: UUID
    document_revision: int = Field(ge=1)
    state: ExamWorkspaceEnrichmentState
    message: str | None = None
    proposals: tuple[ExamWorkspaceAnswerKeyProposalItem, ...] = ()


class ExamWorkspaceExportTarget(StrEnum):
    QTI = "qti"
    PDF = "pdf"
    DOCX = "docx"


class ExamWorkspaceExportFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    filename: str
    media_type: str
    content: bytes
