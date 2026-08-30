"""Protocols for the public Exam Converter runtime.

Purpose:
  Define application-facing seams for transient public job state and local
  conversion execution without coupling the runtime to storage.

Relationships:
  - Implemented by Conversion Hub infrastructure adapters.
  - Used by `application.curated_apps.handlers.public_exam_converter_jobs`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from skriptoteket.application.curated_apps.public_exam_converter import (
    PublicExamConverterSubmittedJob,
    PublicExamConverterUpload,
)


class PublicExamConverterJobStoreProtocol(Protocol):
    async def create(
        self, *, job: PublicExamConverterSubmittedJob
    ) -> PublicExamConverterSubmittedJob: ...

    async def get(
        self, *, public_job_id: str, now: datetime
    ) -> PublicExamConverterSubmittedJob | None: ...

    async def update(
        self, *, job: PublicExamConverterSubmittedJob
    ) -> PublicExamConverterSubmittedJob: ...

    async def count_active(self, *, now: datetime) -> int: ...


class PublicExamConverterLocalExecutorProtocol(Protocol):
    """Enqueue one bounded in-process conversion outside the submit request."""

    async def enqueue(
        self,
        *,
        job: PublicExamConverterSubmittedJob,
        source_dxe: PublicExamConverterUpload,
        graded_result_pdf: PublicExamConverterUpload | None,
        correlation_id: str,
    ) -> None: ...
