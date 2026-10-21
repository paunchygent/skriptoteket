"""Exam answer-key enrichment job contracts.

Purpose:
    Define the durable execution-worker job that produces machine-proposed
    answer keys for one exam workspace source lane (workspace suggestions,
    content tags, DOCX import, DigiExam import), plus its pure lifecycle
    transitions.

Relationships:
    Enqueued by the exam workspace handlers in the same Unit of Work as the
    request that needs it; claimed and processed by the execution worker
    through
    ``application.curated_apps.handlers.exam_answer_key_enrichment_jobs``.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


class ExamAnswerKeyEnrichmentJobStatus(StrEnum):
    """Lifecycle of one machine answer-key enrichment job."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ExamAnswerKeySourceKind(StrEnum):
    """Which source lane one enrichment job completes answer keys for."""

    WORKSPACE = "workspace"
    CONTENT_TAGS = "content_tags"
    DOCX_IMPORT = "docx_import"
    DIGIEXAM_IMPORT = "digiexam_import"


class ExamAnswerKeyEnrichmentJob(BaseModel):
    """Persist one machine answer-key enrichment job."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    source_kind: ExamAnswerKeySourceKind
    owner_user_id: UUID
    status: ExamAnswerKeyEnrichmentJobStatus
    input_filename: str = Field(min_length=1, max_length=255)
    source_dxe: bytes | None = Field(default=None, min_length=1)
    source_docx: bytes | None = Field(default=None, min_length=1)
    workspace_lineage_id: UUID | None = None
    workspace_document_revision: int | None = Field(default=None, ge=1)
    workspace_course_key: str | None = Field(default=None, max_length=64)
    # Editor-sent answer-key views a workspace suggestion job runs on, and the
    # suggestions it produced; both stay on the job, never in an overlay table.
    workspace_request_json: dict[str, JsonValue] | None = None
    workspace_suggestions_json: dict[str, JsonValue] | None = None

    attempts: int = 0
    max_attempts: int = 1
    available_at: datetime
    locked_by: str | None = None
    locked_until: datetime | None = None
    last_error: str | None = None
    diagnostics: tuple[dict[str, JsonValue], ...] = ()
    conversion_progress: dict[str, JsonValue] | None = None

    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @model_validator(mode="after")
    def _source_kind_invariants(self) -> ExamAnswerKeyEnrichmentJob:
        """Check-style invariant: each source lane carries its own binding."""

        if self.source_kind is ExamAnswerKeySourceKind.DIGIEXAM_IMPORT:
            if self.workspace_lineage_id is None or self.workspace_document_revision != 1:
                raise ValueError("DigiExam imports require a version-one workspace binding")
            if self.source_docx is not None:
                raise ValueError("DigiExam imports carry no DOCX bytes")
            if (
                self.workspace_request_json is not None
                or self.workspace_suggestions_json is not None
            ):
                raise ValueError("DigiExam imports carry no answer-key suggestion request")
            terminal = self.status in {
                ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED,
                ExamAnswerKeyEnrichmentJobStatus.FAILED,
            }
            if terminal != (self.source_dxe is None):
                raise ValueError("DigiExam bytes exist only while import is unfinished")
            return self
        if self.source_kind is ExamAnswerKeySourceKind.DOCX_IMPORT:
            if self.workspace_lineage_id is None or self.workspace_document_revision != 1:
                raise ValueError("docx import jobs require a version-one workspace binding")
            if self.source_dxe is not None:
                raise ValueError("docx import jobs carry no DigiExam bytes")
            terminal = self.status in {
                ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED,
                ExamAnswerKeyEnrichmentJobStatus.FAILED,
            }
            if terminal != (self.source_docx is None):
                raise ValueError("docx bytes exist only while conversion is unfinished")
            return self
        if self.source_docx is not None:
            raise ValueError("only docx import jobs carry source_docx")
        if self.workspace_lineage_id is None:
            raise ValueError("workspace enrichment jobs require workspace_lineage_id")
        if self.source_dxe is not None:
            raise ValueError("only DigiExam import jobs carry source_dxe")
        return self


class ExamWorkspaceConversionJobView(BaseModel):
    """Status-poll projection of one enrichment job, without source bytes."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    owner_user_id: UUID
    source_kind: ExamAnswerKeySourceKind
    status: ExamAnswerKeyEnrichmentJobStatus
    workspace_lineage_id: UUID | None
    last_error: str | None
    conversion_progress: dict[str, JsonValue] | None = None


def enqueue_workspace_enrichment_job(
    *,
    job_id: UUID,
    owner_user_id: UUID,
    input_filename: str,
    workspace_lineage_id: UUID,
    workspace_document_revision: int,
    workspace_request_json: dict[str, JsonValue],
    now: datetime,
) -> ExamAnswerKeyEnrichmentJob:
    """Build one queued suggestion job running on editor-sent content.

    ``workspace_document_revision`` is the saved version the editor's copy
    stood on when the teacher asked; a reopened exam finds the job by it.
    """

    return ExamAnswerKeyEnrichmentJob(
        id=job_id,
        source_kind=ExamAnswerKeySourceKind.WORKSPACE,
        owner_user_id=owner_user_id,
        status=ExamAnswerKeyEnrichmentJobStatus.QUEUED,
        input_filename=input_filename,
        source_dxe=None,
        workspace_lineage_id=workspace_lineage_id,
        workspace_document_revision=workspace_document_revision,
        workspace_request_json=workspace_request_json,
        available_at=now,
        created_at=now,
        updated_at=now,
    )


def record_enrichment_attempt(
    *,
    job: ExamAnswerKeyEnrichmentJob,
    now: datetime,
) -> ExamAnswerKeyEnrichmentJob:
    """Record the provider attempt this job is about to make."""

    return job.model_copy(update={"started_at": now, "updated_at": now})


def finish_enrichment_job(
    *,
    job: ExamAnswerKeyEnrichmentJob,
    status: ExamAnswerKeyEnrichmentJobStatus,
    now: datetime,
    last_error: str | None = None,
    diagnostics: tuple[dict[str, JsonValue], ...] | None = None,
) -> ExamAnswerKeyEnrichmentJob:
    """Move one running enrichment job to a terminal status."""

    if status not in {
        ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED,
        ExamAnswerKeyEnrichmentJobStatus.FAILED,
    }:
        raise ValueError("Enrichment jobs finish as succeeded or failed.")
    return job.model_copy(
        update={
            "status": status,
            "last_error": last_error,
            "diagnostics": job.diagnostics if diagnostics is None else diagnostics,
            "locked_by": None,
            "locked_until": None,
            "updated_at": now,
            "finished_at": now,
        }
    )
