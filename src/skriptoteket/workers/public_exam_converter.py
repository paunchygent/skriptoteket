"""Execution-worker lane for durable public Exam Converter jobs."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from uuid import UUID

import structlog
from dishka import AsyncContainer, Scope

from skriptoteket.application.curated_apps.public_exam_converter_local_execution import (
    ProcessPublicExamConverterJobHandler,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_conversion import ExamConversionArtifactStoreProtocol
from skriptoteket.protocols.public_exam_converter import PublicExamConverterJobStoreProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = structlog.get_logger(__name__)


async def process_next_public_exam_converter_job(
    *,
    container: AsyncContainer,
    worker_id: str,
    now: datetime,
    lease_ttl: timedelta,
    clock: ClockProtocol,
) -> bool:
    """Fail-close one expired claim or process one queued public job."""

    async with container(scope=Scope.REQUEST) as request:
        jobs = await request.get(PublicExamConverterJobStoreProtocol)
        handler = await request.get(ProcessPublicExamConverterJobHandler)
        artifacts = await request.get(ExamConversionArtifactStoreProtocol)
        uow = await request.get(UnitOfWorkProtocol)
        async with uow:
            expired_job_id = await jobs.delete_next_expired(now=now)
        if expired_job_id is not None:
            artifacts.delete_artifact(job_id=expired_job_id)
            logger.info(
                "Deleted expired public Exam Converter job",
                job_id=str(expired_job_id),
            )
            return True

        async with uow:
            expired = await jobs.claim_next_expired(
                worker_id=worker_id,
                now=now,
                lease_ttl=lease_ttl,
            )
        if expired is not None:
            await handler.fail_expired(job=expired)
            logger.warning(
                "Public Exam Converter job failed after worker lease expiry",
                job_id=str(expired.local_job_id),
                worker_id=worker_id,
            )
            return True

        async with uow:
            job = await jobs.claim_next(worker_id=worker_id, now=now, lease_ttl=lease_ttl)
        if job is None:
            return False

        stop_heartbeat = asyncio.Event()
        heartbeat_task = asyncio.create_task(
            _heartbeat_loop(
                container=container,
                local_job_id=job.local_job_id,
                worker_id=worker_id,
                lease_ttl=lease_ttl,
                clock=clock,
                stop_event=stop_heartbeat,
            )
        )
        try:
            finished = await handler.handle(job=job)
        finally:
            stop_heartbeat.set()
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
        logger.info(
            "Public Exam Converter job finished",
            job_id=str(finished.local_job_id),
            status=finished.status.value,
        )
        return True


async def _heartbeat_loop(
    *,
    container: AsyncContainer,
    local_job_id: UUID,
    worker_id: str,
    lease_ttl: timedelta,
    clock: ClockProtocol,
    stop_event: asyncio.Event,
) -> None:
    interval = max(1.0, lease_ttl.total_seconds() / 3)
    while not stop_event.is_set():
        await asyncio.sleep(interval)
        if stop_event.is_set():
            return
        async with container(scope=Scope.REQUEST) as request:
            jobs = await request.get(PublicExamConverterJobStoreProtocol)
            uow = await request.get(UnitOfWorkProtocol)
            async with uow:
                renewed = await jobs.heartbeat(
                    local_job_id=local_job_id,
                    worker_id=worker_id,
                    now=clock.now(),
                    lease_ttl=lease_ttl,
                )
        if not renewed:
            logger.warning(
                "Public Exam Converter heartbeat lost its lease",
                job_id=str(local_job_id),
                worker_id=worker_id,
            )
            return
