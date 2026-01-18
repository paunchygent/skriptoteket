from __future__ import annotations

import asyncio
import os
import socket
import time
from datetime import datetime, timedelta
from typing import cast

import structlog
from dishka import Scope

from skriptoteket.config import Settings
from skriptoteket.di import create_container
from skriptoteket.observability.logging import configure_logging
from skriptoteket.observability.tracing import init_tracing
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.execution_queue import ToolRunJobClaim, ToolRunJobRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.run_inputs import RunInputStorageProtocol
from skriptoteket.protocols.runner import ToolRunnerAdoptionProtocol, ToolRunnerProtocol
from skriptoteket.protocols.scripting_ui import (
    BackendActionProviderProtocol,
    UiPayloadNormalizerProtocol,
    UiPolicyProviderProtocol,
)
from skriptoteket.protocols.sleeper import SleeperProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.workers.execution_queue_job_processor import process_claim

logger = structlog.get_logger(__name__)


async def run_execution_queue_worker(
    *,
    queue: str = "default",
    worker_id: str | None = None,
    once: bool = False,
) -> None:
    """Run the Postgres execution-queue worker loop (ADR-0062)."""
    settings = Settings()
    configure_logging(
        service_name=settings.SERVICE_NAME,
        environment=settings.ENVIRONMENT,
        log_level=settings.LOG_LEVEL,
        log_format=settings.LOG_FORMAT,
    )
    if settings.OTEL_TRACING_ENABLED:
        init_tracing(settings.SERVICE_NAME)

    normalized_queue = queue.strip() or "default"
    effective_worker_id = worker_id.strip() if worker_id is not None else ""
    if not effective_worker_id:
        effective_worker_id = f"{socket.gethostname()}:{os.getpid()}:{int(time.time())}"

    container = create_container(settings)
    try:
        clock = await container.get(ClockProtocol)
        sleeper = await container.get(SleeperProtocol)
        runner = await container.get(ToolRunnerProtocol)
        runner_adoption = await container.get(ToolRunnerAdoptionProtocol)
        run_inputs = await container.get(RunInputStorageProtocol)
        ui_policy_provider = await container.get(UiPolicyProviderProtocol)
        backend_actions_provider = await container.get(BackendActionProviderProtocol)
        ui_normalizer = await container.get(UiPayloadNormalizerProtocol)
        id_generator = await container.get(IdGeneratorProtocol)

        lease_ttl = timedelta(seconds=max(1, int(settings.RUNNER_QUEUE_LEASE_TTL_SECONDS)))
        heartbeat_interval = float(settings.RUNNER_QUEUE_HEARTBEAT_INTERVAL_SECONDS)
        poll_interval = float(settings.RUNNER_QUEUE_POLL_INTERVAL_SECONDS)
        reaper_interval = float(settings.RUNNER_QUEUE_REAPER_INTERVAL_SECONDS)
        adopt_missing_backoff_seconds = int(settings.RUNNER_QUEUE_ADOPT_MISSING_BACKOFF_SECONDS)

        logger.info(
            "Execution worker started",
            worker_id=effective_worker_id,
            queue=normalized_queue,
            queue_enabled=settings.RUNNER_QUEUE_ENABLED,
            lease_ttl_seconds=int(lease_ttl.total_seconds()),
            heartbeat_interval_seconds=heartbeat_interval,
            poll_interval_seconds=poll_interval,
            reaper_interval_seconds=reaper_interval,
        )

        loop = asyncio.get_running_loop()
        next_reaper_at = loop.time()

        while True:
            now = clock.now()

            if loop.time() >= next_reaper_at:
                cleared = await _clear_stale_leases(
                    container=container,
                    now=now,
                )
                if cleared:
                    logger.info(
                        "Stale leases cleared",
                        cleared=cleared,
                        queue=normalized_queue,
                    )
                next_reaper_at = loop.time() + reaper_interval

            claim = await _claim_next_job(
                container=container,
                worker_id=effective_worker_id,
                now=now,
                lease_ttl=lease_ttl,
                queue=normalized_queue,
            )
            if claim is None:
                if once:
                    return
                await sleeper.sleep(poll_interval)
                continue

            await process_claim(
                container=container,
                service_name=settings.SERVICE_NAME,
                worker_id=effective_worker_id,
                queue=normalized_queue,
                claim=claim,
                lease_ttl=lease_ttl,
                heartbeat_interval=heartbeat_interval,
                adopt_missing_backoff_seconds=adopt_missing_backoff_seconds,
                runner=runner,
                runner_adoption=runner_adoption,
                run_inputs=run_inputs,
                ui_policy_provider=ui_policy_provider,
                backend_actions_provider=backend_actions_provider,
                ui_normalizer=ui_normalizer,
                clock=clock,
                id_generator=id_generator,
                sleeper=sleeper,
            )

            if once:
                return
    finally:
        await container.close()


async def _clear_stale_leases(*, container, now: datetime) -> int:
    async with container(scope=Scope.REQUEST) as request:
        uow = cast(UnitOfWorkProtocol, await request.get(UnitOfWorkProtocol))
        jobs = cast(ToolRunJobRepositoryProtocol, await request.get(ToolRunJobRepositoryProtocol))
        async with uow:
            return await jobs.clear_stale_leases(now=now)


async def _claim_next_job(
    *,
    container,
    worker_id: str,
    now: datetime,
    lease_ttl: timedelta,
    queue: str,
) -> ToolRunJobClaim | None:
    async with container(scope=Scope.REQUEST) as request:
        uow = cast(UnitOfWorkProtocol, await request.get(UnitOfWorkProtocol))
        jobs = cast(ToolRunJobRepositoryProtocol, await request.get(ToolRunJobRepositoryProtocol))
        async with uow:
            return await jobs.claim_next(
                worker_id=worker_id,
                now=now,
                lease_ttl=lease_ttl,
                queue=queue,
            )
