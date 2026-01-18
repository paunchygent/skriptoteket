from __future__ import annotations

from datetime import datetime, timedelta
from typing import cast
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.errors import not_found
from skriptoteket.domain.scripting.models import RunStatus, ToolRunJob
from skriptoteket.infrastructure.db.models.tool_run import ToolRunModel
from skriptoteket.infrastructure.db.models.tool_run_job import ToolRunJobModel
from skriptoteket.protocols.execution_queue import (
    ToolRunJobClaim,
    ToolRunJobRepositoryProtocol,
)


class PostgreSQLToolRunJobRepository(ToolRunJobRepositoryProtocol):
    """PostgreSQL repository for tool run jobs (execution queue).

    Uses a request-scoped `AsyncSession`; commit/rollback is owned by the Unit of Work.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_run_id(self, *, run_id: UUID) -> ToolRunJob | None:
        stmt = select(ToolRunJobModel).where(ToolRunJobModel.run_id == run_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return ToolRunJob.model_validate(model) if model else None

    async def create(self, *, job: ToolRunJob) -> ToolRunJob:
        model = ToolRunJobModel(
            id=job.id,
            run_id=job.run_id,
            status=job.status,
            queue=job.queue,
            priority=job.priority,
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
        return ToolRunJob.model_validate(model)

    async def update(self, *, job: ToolRunJob) -> ToolRunJob:
        model = await self._session.get(ToolRunJobModel, job.id)
        if model is None:
            raise not_found("ToolRunJob", str(job.id))

        model.status = job.status
        model.queue = job.queue
        model.priority = job.priority
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
        return ToolRunJob.model_validate(model)

    async def claim_next(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
        queue: str = "default",
    ) -> ToolRunJobClaim | None:
        normalized_worker_id = worker_id.strip()
        if not normalized_worker_id:
            raise ValueError("worker_id is required")
        normalized_queue = queue.strip() or "default"

        locked_until = now + lease_ttl

        # 1) Adopt-first: running jobs that have had their lease cleared (locked_until is NULL).
        adopt_stmt = (
            select(ToolRunJobModel)
            .where(ToolRunJobModel.queue == normalized_queue)
            .where(ToolRunJobModel.status == RunStatus.RUNNING.value)
            .where(ToolRunJobModel.locked_until.is_(None))
            .order_by(ToolRunJobModel.priority.desc(), ToolRunJobModel.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        adopt_result = await self._session.execute(adopt_stmt)
        adopt_model = adopt_result.scalar_one_or_none()
        if adopt_model is not None:
            adopt_model.locked_by = normalized_worker_id
            adopt_model.locked_until = locked_until
            adopt_model.updated_at = now
            await self._session.flush()
            await self._session.refresh(adopt_model)
            return ToolRunJobClaim(job=ToolRunJob.model_validate(adopt_model), is_adoption=True)

        # 2) Otherwise, claim queued jobs.
        queued_stmt = (
            select(ToolRunJobModel)
            .where(ToolRunJobModel.queue == normalized_queue)
            .where(ToolRunJobModel.status == RunStatus.QUEUED.value)
            .where(ToolRunJobModel.available_at <= now)
            .where(ToolRunJobModel.attempts < ToolRunJobModel.max_attempts)
            .order_by(ToolRunJobModel.priority.desc(), ToolRunJobModel.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        queued_result = await self._session.execute(queued_stmt)
        queued_model = queued_result.scalar_one_or_none()
        if queued_model is None:
            return None

        queued_model.status = RunStatus.RUNNING.value
        queued_model.locked_by = normalized_worker_id
        queued_model.locked_until = locked_until
        queued_model.updated_at = now
        queued_model.attempts = (queued_model.attempts or 0) + 1
        if queued_model.started_at is None:
            queued_model.started_at = now

        run_model = await self._session.get(ToolRunModel, queued_model.run_id)
        if run_model is not None:
            run_model.status = RunStatus.RUNNING.value
            if run_model.started_at is None:
                run_model.started_at = now

        await self._session.flush()
        await self._session.refresh(queued_model)
        return ToolRunJobClaim(job=ToolRunJob.model_validate(queued_model), is_adoption=False)

    async def heartbeat(
        self,
        *,
        job_id: UUID,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
    ) -> bool:
        normalized_worker_id = worker_id.strip()
        if not normalized_worker_id:
            raise ValueError("worker_id is required")

        locked_until = now + lease_ttl

        stmt = (
            update(ToolRunJobModel)
            .where(ToolRunJobModel.id == job_id)
            .where(ToolRunJobModel.status == RunStatus.RUNNING.value)
            .where(ToolRunJobModel.locked_by == normalized_worker_id)
            .values(
                locked_until=locked_until,
                updated_at=now,
            )
        )
        result = await self._session.execute(stmt)
        cursor_result = cast(CursorResult, result)
        await self._session.flush()
        return bool(cursor_result.rowcount and cursor_result.rowcount > 0)

    async def clear_stale_leases(self, *, now: datetime) -> int:
        stmt = (
            update(ToolRunJobModel)
            .where(ToolRunJobModel.status == RunStatus.RUNNING.value)
            .where(
                and_(ToolRunJobModel.locked_until.is_not(None), ToolRunJobModel.locked_until < now)
            )
            .values(
                locked_by=None,
                locked_until=None,
                updated_at=now,
            )
        )
        result = await self._session.execute(stmt)
        cursor_result = cast(CursorResult, result)
        await self._session.flush()
        return int(cursor_result.rowcount or 0)
