"""Exam answer-key enrichment job contracts.

Purpose:
    Define the durable execution-worker job that produces machine-proposed
    answer keys for one in-process Exam Converter conversion, plus its pure
    lifecycle transitions.

Relationships:
    Enqueued by ``application.curated_apps.handlers.exam_converter_conversions``
    in the same Unit of Work as the conversion job; claimed and processed by
    the execution worker through
    ``application.curated_apps.handlers.exam_answer_key_enrichment_jobs``.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class ExamAnswerKeyEnrichmentJobStatus(StrEnum):
    """Lifecycle of one machine answer-key enrichment job."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ExamAnswerKeyEnrichmentJob(BaseModel):
    """Persist one machine answer-key enrichment job."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    conversion_job_id: UUID
    owner_user_id: UUID
    status: ExamAnswerKeyEnrichmentJobStatus
    input_filename: str = Field(min_length=1, max_length=255)
    source_dxe: bytes = Field(min_length=1)
    retry_identity: str | None = Field(default=None, max_length=255)

    attempts: int = 0
    max_attempts: int = 1
    available_at: datetime
    locked_by: str | None = None
    locked_until: datetime | None = None
    last_error: str | None = None

    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ExamAnswerKeyProposedOverlay(BaseModel):
    """Persist one machine-proposed answer-key overlay as a proposal record."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    enrichment_job_id: UUID
    conversion_job_id: UUID
    owner_user_id: UUID
    source_file_sha256: str = Field(min_length=1, max_length=128)
    source_ir_sha256: str = Field(min_length=1, max_length=128)
    provider_profile_id: str = Field(min_length=1, max_length=128)
    model: str = Field(min_length=1, max_length=128)
    overlay_json: dict[str, JsonValue]
    created_at: datetime


def enqueue_enrichment_job(
    *,
    job_id: UUID,
    conversion_job_id: UUID,
    owner_user_id: UUID,
    input_filename: str,
    source_dxe: bytes,
    now: datetime,
    retry_identity: str | None = None,
) -> ExamAnswerKeyEnrichmentJob:
    """Build one queued enrichment job for a submitted conversion."""

    return ExamAnswerKeyEnrichmentJob(
        id=job_id,
        conversion_job_id=conversion_job_id,
        owner_user_id=owner_user_id,
        status=ExamAnswerKeyEnrichmentJobStatus.QUEUED,
        input_filename=input_filename,
        source_dxe=source_dxe,
        retry_identity=retry_identity,
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
            "locked_by": None,
            "locked_until": None,
            "updated_at": now,
            "finished_at": now,
        }
    )
