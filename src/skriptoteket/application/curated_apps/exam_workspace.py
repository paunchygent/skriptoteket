"""Exam workspace application DTOs (ST-SKRIPT-39-04 walking skeleton)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)


class ExamWorkspaceDocumentSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    lineage_id: UUID
    version: int = Field(ge=1)
    vault_file_id: UUID
    name: str
    saved_at: datetime


class ExamWorkspaceDocumentResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    document: NativeExamDocument
    summary: ExamWorkspaceDocumentSummary
    notes: tuple[str, ...] = ()


class ExamWorkspaceConversionStatus(BaseModel):
    """Owner-visible status of one background DOCX import."""

    model_config = ConfigDict(frozen=True)

    job_id: UUID
    lineage_id: UUID
    state: Literal["queued", "running", "succeeded", "failed"]
    error_message: str | None = None


class ExamWorkspaceDocumentListResponse(BaseModel):
    """The actor's workspace documents, one head version per lineage."""

    model_config = ConfigDict(frozen=True)

    documents: tuple[ExamWorkspaceDocumentSummary, ...] = ()


class SaveExamWorkspaceDocumentRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    expected_revision: int = Field(ge=1)
    document: NativeExamDocument
    rejected_proposal_item_ids: tuple[str, ...] = ()
