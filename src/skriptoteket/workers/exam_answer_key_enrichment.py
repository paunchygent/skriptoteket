"""Execution-worker lane for machine answer-key enrichment jobs.

Purpose:
    Claim and process one queued answer-key enrichment job inside the
    existing execution-worker process (`skriptoteket.cli run-execution-worker`)
    so remote provider calls never run inside a web request.

Relationships:
    Called from ``workers.execution_queue_worker`` on each loop iteration;
    claiming uses the SKIP LOCKED repository and processing runs through
    ``application.curated_apps.handlers.exam_answer_key_enrichment_jobs``.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import structlog
from dishka import AsyncContainer, Scope

from skriptoteket.application.curated_apps.handlers.exam_answer_key_enrichment_jobs import (
    ProcessExamAnswerKeyEnrichmentJobHandler,
)
from skriptoteket.protocols.exam_answer_key import ExamAnswerKeyEnrichmentJobRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = structlog.get_logger(__name__)


async def process_next_answer_key_enrichment_job(
    *,
    container: AsyncContainer,
    worker_id: str,
    now: datetime,
    lease_ttl: timedelta,
) -> bool:
    """Advance the enrichment lane by one step; report whether one step ran.

    Each invocation first fail-closes at most one RUNNING job whose worker
    lease expired (a crashed worker; no retry), then claims and processes at
    most one queued job.
    """

    async with container(scope=Scope.REQUEST) as request:
        handler = await request.get(ProcessExamAnswerKeyEnrichmentJobHandler)
        expired = await handler.fail_next_expired(now=now)
        if expired is not None:
            logger.warning(
                "Answer-key enrichment job fail-closed after worker lease expiry",
                job_id=str(expired.id),
                conversion_job_id=str(expired.conversion_job_id),
                worker_id=worker_id,
            )
            return True
        uow = await request.get(UnitOfWorkProtocol)
        jobs = await request.get(ExamAnswerKeyEnrichmentJobRepositoryProtocol)
        async with uow:
            job = await jobs.claim_next(worker_id=worker_id, now=now, lease_ttl=lease_ttl)
        if job is None:
            return False
        logger.info(
            "Answer-key enrichment job claimed",
            job_id=str(job.id),
            conversion_job_id=str(job.conversion_job_id),
            worker_id=worker_id,
        )
        finished = await handler.handle(job=job)
        logger.info(
            "Answer-key enrichment job finished",
            job_id=str(finished.id),
            status=finished.status.value,
            last_error=finished.last_error,
        )
        return True
