"""Protocols for Exam Converter correction-session persistence.

Purpose:
  Define the repository seam for Skriptoteket-owned durable correction intents
  without coupling application code to SQLAlchemy storage.

Relationships:
  - Used by ST-21-04 application handlers and replay orchestration.
  - Implemented by the PostgreSQL correction-session repository.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from skriptoteket.domain.curated_apps.exam_converter_correction_sessions import (
    ExamConverterCorrectionSession,
)


class ExamConverterCorrectionSessionRepositoryProtocol(Protocol):
    """Persist owner-scoped Exam Converter correction sessions."""

    async def get_by_owner_and_job(
        self,
        *,
        owner_user_id: UUID,
        conversion_hub_job_id: UUID,
    ) -> ExamConverterCorrectionSession | None: ...

    async def save(
        self,
        *,
        session: ExamConverterCorrectionSession,
        expected_session_version: int,
    ) -> ExamConverterCorrectionSession: ...


class ExamConverterCorrectionMutationRepositoryProtocol(
    ExamConverterCorrectionSessionRepositoryProtocol, Protocol
):
    """Correction persistence serialized by its always-present parent job."""

    async def lock_owned_job(
        self,
        *,
        owner_user_id: UUID,
        conversion_hub_job_id: UUID,
    ) -> None: ...


class ExamConverterReplayCorrectionSessionRepositoryProtocol(
    ExamConverterCorrectionMutationRepositoryProtocol, Protocol
):
    """Correction-session repository with replay publication locking."""

    async def get_by_owner_and_job_for_update(
        self,
        *,
        owner_user_id: UUID,
        conversion_hub_job_id: UUID,
    ) -> ExamConverterCorrectionSession | None: ...
