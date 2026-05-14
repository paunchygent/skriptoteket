"""In-memory public Exam Converter transient job store.

Purpose:
  Retain opaque public job handles, upstream ids, and server-side grants only
  for the short anonymous artifact lifetime required by the public runtime.

Relationships:
  - Implements `PublicExamConverterJobStoreProtocol`.
  - Used by the public Exam Converter application handler.
  - Deliberately separate from authenticated Conversion Hub repositories,
    Vault files, and account-owned job ledgers.
"""

from __future__ import annotations

from datetime import datetime

from skriptoteket.application.curated_apps.public_exam_converter import (
    PublicExamConverterJobStatus,
    PublicExamConverterSubmittedJob,
)

_TERMINAL_STATUSES = frozenset(
    {
        PublicExamConverterJobStatus.SUCCEEDED,
        PublicExamConverterJobStatus.FAILED,
        PublicExamConverterJobStatus.CANCELED,
        PublicExamConverterJobStatus.EXPIRED,
    }
)


class InMemoryPublicExamConverterJobStore:
    """Store public jobs in process memory until their artifact TTL expires."""

    def __init__(self) -> None:
        self._jobs: dict[str, PublicExamConverterSubmittedJob] = {}

    async def create(
        self,
        *,
        job: PublicExamConverterSubmittedJob,
    ) -> PublicExamConverterSubmittedJob:
        self._jobs[job.public_job_id] = job
        return job

    async def get(
        self,
        *,
        public_job_id: str,
        now: datetime,
    ) -> PublicExamConverterSubmittedJob | None:
        self._purge_expired(now=now)
        job = self._jobs.get(public_job_id)
        if job is None:
            return None
        if job.expires_at <= now:
            self._jobs.pop(public_job_id, None)
            return None
        return job

    async def update(
        self,
        *,
        job: PublicExamConverterSubmittedJob,
    ) -> PublicExamConverterSubmittedJob:
        self._jobs[job.public_job_id] = job
        return job

    async def count_active(self, *, now: datetime) -> int:
        self._purge_expired(now=now)
        return sum(1 for job in self._jobs.values() if job.status not in _TERMINAL_STATUSES)

    def _purge_expired(self, *, now: datetime) -> None:
        expired_ids = [
            public_job_id for public_job_id, job in self._jobs.items() if job.expires_at <= now
        ]
        for public_job_id in expired_ids:
            self._jobs.pop(public_job_id, None)
