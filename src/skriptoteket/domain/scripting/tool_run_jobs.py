from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.domain.scripting.tool_runs import RunStatus


class ToolRunJob(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    run_id: UUID
    status: RunStatus

    queue: str = "default"
    priority: int = 0

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

    @model_validator(mode="after")
    def _validate_attempts(self) -> "ToolRunJob":
        if self.attempts < 0:
            raise ValueError("attempts must be >= 0")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.attempts > self.max_attempts:
            raise ValueError("attempts must be <= max_attempts")
        return self


def enqueue_job(
    *,
    job_id: UUID,
    run_id: UUID,
    now: datetime,
    queue: str = "default",
    priority: int = 0,
    max_attempts: int = 1,
) -> ToolRunJob:
    normalized_queue = queue.strip()
    if not normalized_queue:
        raise validation_error("queue is required")
    if max_attempts < 1:
        raise validation_error("max_attempts must be >= 1")

    return ToolRunJob(
        id=job_id,
        run_id=run_id,
        status=RunStatus.QUEUED,
        queue=normalized_queue,
        priority=priority,
        attempts=0,
        max_attempts=max_attempts,
        available_at=now,
        locked_by=None,
        locked_until=None,
        last_error=None,
        created_at=now,
        updated_at=now,
        started_at=None,
        finished_at=None,
    )


def lease_job(
    *,
    job: ToolRunJob,
    worker_id: str,
    now: datetime,
    lease_ttl: timedelta,
) -> ToolRunJob:
    normalized_worker_id = worker_id.strip()
    if not normalized_worker_id:
        raise validation_error("worker_id is required")
    if lease_ttl.total_seconds() <= 0:
        raise validation_error("lease_ttl must be > 0 seconds")

    return job.model_copy(
        update={
            "locked_by": normalized_worker_id,
            "locked_until": now + lease_ttl,
            "updated_at": now,
        }
    )


def clear_lease(
    *,
    job: ToolRunJob,
    now: datetime,
) -> ToolRunJob:
    return job.model_copy(
        update={
            "locked_by": None,
            "locked_until": None,
            "updated_at": now,
        }
    )


def mark_job_started(*, job: ToolRunJob, now: datetime) -> ToolRunJob:
    if job.status is not RunStatus.QUEUED:
        raise DomainError(
            code=ErrorCode.CONFLICT,
            message="Only queued jobs can be started",
            details={"status": job.status.value},
        )
    if now < job.available_at:
        raise validation_error(
            "started_at cannot be before available_at",
            details={"available_at": job.available_at.isoformat(), "started_at": now.isoformat()},
        )
    return job.model_copy(
        update={
            "status": RunStatus.RUNNING,
            "started_at": now,
            "updated_at": now,
        }
    )


def mark_job_finished(*, job: ToolRunJob, status: RunStatus, now: datetime) -> ToolRunJob:
    if job.status is not RunStatus.RUNNING:
        raise DomainError(
            code=ErrorCode.CONFLICT,
            message="Only running jobs can be finished",
            details={"status": job.status.value},
        )
    if status in {RunStatus.QUEUED, RunStatus.RUNNING}:
        raise validation_error("finish requires a terminal status")
    if job.started_at is not None and now < job.started_at:
        raise validation_error(
            "finished_at cannot be before started_at",
            details={"started_at": job.started_at.isoformat(), "finished_at": now.isoformat()},
        )
    return job.model_copy(
        update={
            "status": status,
            "finished_at": now,
            "locked_by": None,
            "locked_until": None,
            "updated_at": now,
        }
    )


def requeue_job_with_backoff(
    *,
    job: ToolRunJob,
    now: datetime,
    available_at: datetime,
    last_error: str | None = None,
) -> ToolRunJob:
    if job.status is not RunStatus.RUNNING:
        raise DomainError(
            code=ErrorCode.CONFLICT,
            message="Only running jobs can be requeued",
            details={"status": job.status.value},
        )
    if available_at < now:
        raise validation_error(
            "available_at cannot be before now",
            details={"available_at": available_at.isoformat(), "now": now.isoformat()},
        )

    return job.model_copy(
        update={
            "status": RunStatus.QUEUED,
            "available_at": available_at,
            "locked_by": None,
            "locked_until": None,
            "last_error": last_error,
            "updated_at": now,
        }
    )
