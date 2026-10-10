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
