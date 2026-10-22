"""Execution-worker lane for machine answer-key enrichment jobs.

Purpose:
    Claim and process queued answer-key enrichment jobs inside the existing
    execution-worker process (`skriptoteket.cli run-execution-worker`) so
    remote provider calls never run inside a web request. The worker runs
    ``LLM_WORKER_JOB_CONCURRENCY`` slots; each slot is one coroutine that
    advances the lane one step at a time under its own worker id, so the lease
    fence (``locked_by``) and expired-lease recovery stay per job.

Relationships:
    ``workers.execution_queue_worker`` starts the slots (and calls one step
    directly for ``--once``); claiming uses the SKIP LOCKED repository, which
    hands each queued job to exactly one slot, and processing runs through
    ``application.curated_apps.handlers.exam_answer_key_enrichment_jobs``.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from uuid import UUID

import structlog
from dishka import AsyncContainer, Scope

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import ExamAnswerKeySourceKind
from skriptoteket.application.curated_apps.handlers.exam_answer_key_enrichment_jobs import (
    ProcessExamAnswerKeyEnrichmentJobHandler,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import ExamAnswerKeyEnrichmentJobRepositoryProtocol
from skriptoteket.protocols.sleeper import SleeperProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = structlog.get_logger(__name__)


def enrichment_slot_worker_id(*, worker_id: str, slot: int) -> str:
    """Return the lease identity of one enrichment slot of a worker process."""

    return f"{worker_id}:{slot}"


async def run_answer_key_enrichment_slot(
    *,
    container: AsyncContainer,
    worker_id: str,
    lease_ttl: timedelta,
    clock: ClockProtocol,
    sleeper: SleeperProtocol,
    poll_interval: float,
    enrichment_enabled: bool,
) -> None:
    """Advance the enrichment lane forever as one slot, polling when idle."""

    while True:
        advanced = await process_next_answer_key_enrichment_job(
            container=container,
            worker_id=worker_id,
            now=clock.now(),
            lease_ttl=lease_ttl,
            clock=clock,
            enrichment_enabled=enrichment_enabled,
        )
        if not advanced:
            await sleeper.sleep(poll_interval)


async def process_next_answer_key_enrichment_job(
    *,
    container: AsyncContainer,
    worker_id: str,
    now: datetime,
    lease_ttl: timedelta,
    clock: ClockProtocol,
    enrichment_enabled: bool = True,
) -> bool:
    """Advance the enrichment lane by one step; report whether one step ran.

    Each invocation first fail-closes at most one RUNNING job whose worker
    lease expired (a crashed worker; no retry), then claims and processes at
    most one queued job.
    """

    async with container(scope=Scope.REQUEST) as request:
        handler = await request.get(ProcessExamAnswerKeyEnrichmentJobHandler)
        if enrichment_enabled:
            expired = await handler.fail_next_expired(
                worker_id=worker_id,
                now=now,
                lease_ttl=lease_ttl,
            )
        else:
            expired = await handler.fail_next_expired(
                worker_id=worker_id,
                now=now,
                lease_ttl=lease_ttl,
                source_kind=ExamAnswerKeySourceKind.DOCX_IMPORT,
            )
            if expired is None:
                expired = await handler.fail_next_expired(
                    worker_id=worker_id,
                    now=now,
                    lease_ttl=lease_ttl,
                    source_kind=ExamAnswerKeySourceKind.DIGIEXAM_IMPORT,
                )
        if expired is not None:
            logger.warning(
                "Answer-key enrichment job fail-closed after worker lease expiry",
                job_id=str(expired.id),
                worker_id=worker_id,
            )
            return True
        uow = await request.get(UnitOfWorkProtocol)
        jobs = await request.get(ExamAnswerKeyEnrichmentJobRepositoryProtocol)
        async with uow:
            if enrichment_enabled:
                job = await jobs.claim_next(worker_id=worker_id, now=now, lease_ttl=lease_ttl)
            else:
                job = await jobs.claim_next(
                    worker_id=worker_id,
                    now=now,
                    lease_ttl=lease_ttl,
                    source_kind=ExamAnswerKeySourceKind.DOCX_IMPORT,
                )
                if job is None:
                    job = await jobs.claim_next(
                        worker_id=worker_id,
                        now=now,
                        lease_ttl=lease_ttl,
                        source_kind=ExamAnswerKeySourceKind.DIGIEXAM_IMPORT,
                    )
        if job is None:
            return False
        logger.info(
            "Exam enrichment queue job claimed",
            job_id=str(job.id),
            worker_id=worker_id,
            source_kind=job.source_kind.value,
        )
        stop_heartbeat = asyncio.Event()
        heartbeat_task = asyncio.create_task(
            _heartbeat_loop(
                container=container,
                job_id=job.id,
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
            "Exam enrichment queue job finished",
            job_id=str(finished.id),
            status=finished.status.value,
            last_error=finished.last_error,
            source_kind=finished.source_kind.value,
        )
        return True


async def _heartbeat_loop(
    *,
    container: AsyncContainer,
    job_id: UUID,
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
            jobs = await request.get(ExamAnswerKeyEnrichmentJobRepositoryProtocol)
            uow = await request.get(UnitOfWorkProtocol)
            async with uow:
                renewed = await jobs.heartbeat(
                    job_id=job_id,
                    worker_id=worker_id,
                    now=clock.now(),
                    lease_ttl=lease_ttl,
                )
        if not renewed:
            logger.warning(
                "Answer-key enrichment heartbeat lost its lease",
                job_id=str(job_id),
                worker_id=worker_id,
            )
            return
