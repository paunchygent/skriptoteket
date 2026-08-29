"""PostgreSQL repository for machine answer-key enrichment jobs.

Purpose:
    Persist and claim the execution-worker jobs that produce machine-proposed
    answer keys, using the same FOR UPDATE SKIP LOCKED claim discipline as the
    tool-run execution queue.

Relationships:
    Implements ``ExamAnswerKeyEnrichmentJobRepositoryProtocol`` on a
    request-scoped ``AsyncSession``; commit/rollback is owned by the UoW.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
)
from skriptoteket.domain.errors import not_found
from skriptoteket.infrastructure.db.models.exam_answer_key_enrichment_job import (
    ExamAnswerKeyEnrichmentJobModel,
)
from skriptoteket.protocols.exam_answer_key import ExamAnswerKeyEnrichmentJobRepositoryProtocol


class PostgreSQLExamAnswerKeyEnrichmentJobRepository(ExamAnswerKeyEnrichmentJobRepositoryProtocol):
    """Postgres enrichment-job ledger with SKIP LOCKED claims."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, job: ExamAnswerKeyEnrichmentJob) -> ExamAnswerKeyEnrichmentJob:
        model = ExamAnswerKeyEnrichmentJobModel(
            id=job.id,
            conversion_job_id=job.conversion_job_id,
            owner_user_id=job.owner_user_id,
            status=job.status.value,
            input_filename=job.input_filename,
            source_dxe=job.source_dxe,
            attempts=job.attempts,
            max_attempts=job.max_attempts,
            available_at=job.available_at,
            locked_by=job.locked_by,
            locked_until=job.locked_until,
            last_error=job.last_error,
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return ExamAnswerKeyEnrichmentJob.model_validate(model)

    async def update(self, *, job: ExamAnswerKeyEnrichmentJob) -> ExamAnswerKeyEnrichmentJob:
        model = await self._session.get(ExamAnswerKeyEnrichmentJobModel, job.id)
        if model is None:
            raise not_found("ExamAnswerKeyEnrichmentJob", str(job.id))
        model.status = job.status.value
        model.attempts = job.attempts
        model.max_attempts = job.max_attempts
        model.available_at = job.available_at
        model.locked_by = job.locked_by
        model.locked_until = job.locked_until
        model.last_error = job.last_error
        model.updated_at = job.updated_at
        model.started_at = job.started_at
        model.finished_at = job.finished_at
        await self._session.flush()
        await self._session.refresh(model)
        return ExamAnswerKeyEnrichmentJob.model_validate(model)

    async def get_by_id(self, *, job_id: UUID) -> ExamAnswerKeyEnrichmentJob | None:
        model = await self._session.get(ExamAnswerKeyEnrichmentJobModel, job_id)
        return ExamAnswerKeyEnrichmentJob.model_validate(model) if model else None

    async def claim_next(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
    ) -> ExamAnswerKeyEnrichmentJob | None:
        normalized_worker_id = worker_id.strip()
        if not normalized_worker_id:
            raise ValueError("worker_id is required")
        stmt = (
            select(ExamAnswerKeyEnrichmentJobModel)
            .where(
                ExamAnswerKeyEnrichmentJobModel.attempts
                < ExamAnswerKeyEnrichmentJobModel.max_attempts
            )
            .where(
                or_(
                    and_(
                        ExamAnswerKeyEnrichmentJobModel.status
                        == ExamAnswerKeyEnrichmentJobStatus.QUEUED.value,
                        ExamAnswerKeyEnrichmentJobModel.available_at <= now,
                    ),
                    and_(
                        ExamAnswerKeyEnrichmentJobModel.status
                        == ExamAnswerKeyEnrichmentJobStatus.RUNNING.value,
                        ExamAnswerKeyEnrichmentJobModel.locked_until.is_not(None),
                        ExamAnswerKeyEnrichmentJobModel.locked_until < now,
                    ),
                )
            )
            .order_by(ExamAnswerKeyEnrichmentJobModel.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        model.status = ExamAnswerKeyEnrichmentJobStatus.RUNNING.value
        model.attempts = model.attempts + 1
        model.locked_by = normalized_worker_id
        model.locked_until = now + lease_ttl
        model.updated_at = now
        await self._session.flush()
        await self._session.refresh(model)
        return ExamAnswerKeyEnrichmentJob.model_validate(model)
