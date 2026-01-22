import asyncio
from datetime import timedelta

import structlog

from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.sleeper import SleeperProtocol
from skriptoteket.workers.execution_queue_job_db import heartbeat_once

logger = structlog.get_logger(__name__)


async def heartbeat_loop(
    *,
    container,
    sleeper: SleeperProtocol,
    clock: ClockProtocol,
    job_id,
    worker_id: str,
    lease_ttl: timedelta,
    interval_seconds: float,
    stop_event: asyncio.Event,
) -> None:
    interval = max(1.0, float(interval_seconds))
    while not stop_event.is_set():
        await sleeper.sleep(interval)
        if stop_event.is_set():
            return
        now = clock.now()
        try:
            ok = await heartbeat_once(
                container=container,
                job_id=job_id,
                worker_id=worker_id,
                now=now,
                lease_ttl=lease_ttl,
            )
            if not ok:
                logger.warning(
                    "Heartbeat failed (lease lost?)",
                    job_id=str(job_id),
                    worker_id=worker_id,
                )
        except Exception:  # noqa: BLE001
            logger.exception(
                "Heartbeat failed (unexpected exception)",
                job_id=str(job_id),
                worker_id=worker_id,
            )
