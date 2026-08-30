"""PostgreSQL repository for anonymous Exam Converter jobs."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.public_exam_converter import (
    PublicExamConverterJobStatus,
    PublicExamConverterSubmittedJob,
    PublicExamConverterTarget,
    PublicExamConverterUpload,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.infrastructure.db.models.public_exam_converter_job import (
    PublicExamConverterJobModel,
)
from skriptoteket.protocols.public_exam_converter import PublicExamConverterJobStoreProtocol

_ACTIVE_STATUSES = (
    PublicExamConverterJobStatus.QUEUED.value,
    PublicExamConverterJobStatus.PROCESSING.value,
)


class PostgreSQLPublicExamConverterJobRepository(PublicExamConverterJobStoreProtocol):
    """Own public job state, capacity, claims, and worker leases in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_if_capacity(
        self,
        *,
        job: PublicExamConverterSubmittedJob,
        now: datetime,
        concurrency_limit: int,
    ) -> PublicExamConverterSubmittedJob | None:
        if concurrency_limit < 1:
            raise ValueError("concurrency_limit must be positive")
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": "public-exam-converter-capacity"},
        )
        active = await self._session.scalar(
            select(func.count())
            .select_from(PublicExamConverterJobModel)
            .where(
                PublicExamConverterJobModel.status.in_(_ACTIVE_STATUSES),
                PublicExamConverterJobModel.expires_at > now,
            )
        )
        if int(active or 0) >= concurrency_limit:
            return None
        model = self._to_model(job)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_job(model)

    async def get(
        self,
        *,
        public_job_id: str,
        now: datetime,
    ) -> PublicExamConverterSubmittedJob | None:
        try:
            job_id = UUID(public_job_id)
        except ValueError:
            return None
        model = await self._session.get(PublicExamConverterJobModel, job_id)
        if model is None or model.expires_at <= now:
            return None
        return self._to_job(model)

    async def update(
        self,
        *,
        job: PublicExamConverterSubmittedJob,
        expected_worker_id: str | None = None,
    ) -> PublicExamConverterSubmittedJob:
        model = await self._session.get(PublicExamConverterJobModel, job.local_job_id)
        if model is None:
            raise not_found("PublicExamConverterJob", str(job.local_job_id))
        if expected_worker_id is not None and model.locked_by != expected_worker_id:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message="Public Exam Converter worker lease is no longer owned.",
            )
        model.status = job.status.value
        model.updated_at = job.updated_at
        model.locked_by = job.locked_by
        model.locked_until = job.locked_until
        model.error_message = job.error_message
        model.result = job.result
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_job(model)

    async def claim_next(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
    ) -> PublicExamConverterSubmittedJob | None:
        return await self._claim(
            worker_id=worker_id,
            now=now,
            lease_ttl=lease_ttl,
            expired=False,
        )

    async def claim_next_expired(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
    ) -> PublicExamConverterSubmittedJob | None:
        return await self._claim(
            worker_id=worker_id,
            now=now,
            lease_ttl=lease_ttl,
            expired=True,
        )

    async def heartbeat(
        self,
        *,
        local_job_id: UUID,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
    ) -> bool:
        renewed_id = await self._session.scalar(
            update(PublicExamConverterJobModel)
            .where(
                PublicExamConverterJobModel.id == local_job_id,
                PublicExamConverterJobModel.status == PublicExamConverterJobStatus.PROCESSING.value,
                PublicExamConverterJobModel.locked_by == worker_id,
            )
            .values(locked_until=now + lease_ttl, updated_at=now)
            .returning(PublicExamConverterJobModel.id)
        )
        return renewed_id is not None

    async def delete_next_expired(self, *, now: datetime) -> UUID | None:
        expired_id = await self._session.scalar(
            select(PublicExamConverterJobModel.id)
            .where(
                PublicExamConverterJobModel.expires_at <= now,
                or_(
                    PublicExamConverterJobModel.status
                    != PublicExamConverterJobStatus.PROCESSING.value,
                    PublicExamConverterJobModel.locked_until.is_(None),
                    PublicExamConverterJobModel.locked_until < now,
                ),
            )
            .order_by(PublicExamConverterJobModel.expires_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if expired_id is None:
            return None
        deleted_id = await self._session.scalar(
            delete(PublicExamConverterJobModel)
            .where(PublicExamConverterJobModel.id == expired_id)
            .returning(PublicExamConverterJobModel.id)
        )
        return deleted_id

    async def _claim(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
        expired: bool,
    ) -> PublicExamConverterSubmittedJob | None:
        normalized_worker_id = worker_id.strip()
        if not normalized_worker_id:
            raise ValueError("worker_id is required")
        status = (
            PublicExamConverterJobStatus.PROCESSING.value
            if expired
            else PublicExamConverterJobStatus.QUEUED.value
        )
        statement = select(PublicExamConverterJobModel).where(
            PublicExamConverterJobModel.status == status,
            PublicExamConverterJobModel.expires_at > now,
        )
        if expired:
            statement = statement.where(
                PublicExamConverterJobModel.locked_until.is_not(None),
                PublicExamConverterJobModel.locked_until < now,
            )
        statement = (
            statement.order_by(PublicExamConverterJobModel.submitted_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        model = (await self._session.execute(statement)).scalar_one_or_none()
        if model is None:
            return None
        model.status = PublicExamConverterJobStatus.PROCESSING.value
        model.locked_by = normalized_worker_id
        model.locked_until = now + lease_ttl
        model.updated_at = now
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_job(model)

    @staticmethod
    def _to_model(job: PublicExamConverterSubmittedJob) -> PublicExamConverterJobModel:
        graded = job.graded_result_pdf
        return PublicExamConverterJobModel(
            id=job.local_job_id,
            status=job.status.value,
            requested_targets=[target.value for target in job.requested_targets],
            source_filename=job.source_dxe.filename,
            source_content_type=job.source_dxe.content_type,
            source_dxe=job.source_dxe.file_bytes,
            graded_result_filename=graded.filename if graded is not None else None,
            graded_result_content_type=graded.content_type if graded is not None else None,
            graded_result_pdf=graded.file_bytes if graded is not None else None,
            correlation_id=job.correlation_id,
            error_message=job.error_message,
            result=job.result,
            locked_by=job.locked_by,
            locked_until=job.locked_until,
            submitted_at=job.submitted_at,
            updated_at=job.updated_at,
            expires_at=job.expires_at,
        )

    @staticmethod
    def _to_job(model: PublicExamConverterJobModel) -> PublicExamConverterSubmittedJob:
        graded = None
        if model.graded_result_pdf is not None:
            graded = PublicExamConverterUpload(
                filename=model.graded_result_filename or "graded-result.pdf",
                content_type=model.graded_result_content_type or "application/pdf",
                file_bytes=model.graded_result_pdf,
            )
        return PublicExamConverterSubmittedJob(
            public_job_id=str(model.id),
            local_job_id=model.id,
            requested_targets=tuple(
                PublicExamConverterTarget(value) for value in model.requested_targets
            ),
            status=PublicExamConverterJobStatus(model.status),
            source_filename=model.source_filename,
            submitted_at=model.submitted_at,
            updated_at=model.updated_at,
            expires_at=model.expires_at,
            correlation_id=model.correlation_id,
            source_dxe=PublicExamConverterUpload(
                filename=model.source_filename,
                content_type=model.source_content_type,
                file_bytes=model.source_dxe,
            ),
            graded_result_pdf=graded,
            locked_by=model.locked_by,
            locked_until=model.locked_until,
            error_message=model.error_message,
            result=model.result,
        )
