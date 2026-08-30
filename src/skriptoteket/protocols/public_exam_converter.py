"""Protocols for the public Exam Converter runtime.

Purpose:
  Define application-facing seams for transient public job state and local
  conversion execution without coupling the runtime to storage.

Relationships:
  - Implemented by Conversion Hub infrastructure adapters.
  - Used by `application.curated_apps.handlers.public_exam_converter_jobs`.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from skriptoteket.application.curated_apps.public_exam_converter import (
    PublicExamConverterSubmittedJob,
)


class PublicExamConverterJobStoreProtocol(Protocol):
    async def create_if_capacity(
        self,
        *,
        job: PublicExamConverterSubmittedJob,
        now: datetime,
        concurrency_limit: int,
    ) -> PublicExamConverterSubmittedJob | None: ...

    async def get(
        self, *, public_job_id: str, now: datetime
    ) -> PublicExamConverterSubmittedJob | None: ...

    async def update(
        self,
        *,
        job: PublicExamConverterSubmittedJob,
        expected_worker_id: str | None = None,
    ) -> PublicExamConverterSubmittedJob: ...

    async def claim_next(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
    ) -> PublicExamConverterSubmittedJob | None: ...

    async def claim_next_expired(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
    ) -> PublicExamConverterSubmittedJob | None: ...

    async def heartbeat(
        self,
        *,
        local_job_id: UUID,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
    ) -> bool: ...

    async def delete_next_expired(self, *, now: datetime) -> UUID | None: ...
