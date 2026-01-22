from __future__ import annotations

import asyncio
import time
from datetime import timedelta

import structlog

from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.scripting.tool_run_jobs import mark_job_finished
from skriptoteket.domain.scripting.tool_runs import finish_run
from skriptoteket.observability.tracing import get_tracer, trace_operation
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.execution_queue import ToolRunJobClaim
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.run_inputs import RunInputStorageProtocol
from skriptoteket.protocols.runner import ToolRunnerAdoptionProtocol, ToolRunnerProtocol
from skriptoteket.protocols.scripting_ui import (
    BackendActionProviderProtocol,
    UiPayloadNormalizerProtocol,
    UiPolicyProviderProtocol,
)
from skriptoteket.protocols.sleeper import SleeperProtocol
from skriptoteket.workers.execution_queue_job_db import (
    finalize_job,
    finalize_job_as_failed,
    load_execution_context,
    requeue_missing_adoptable_container,
)

from .execution import run_execution_attempt
from .heartbeat import heartbeat_loop
from .normalization import normalize_ui_payload

logger = structlog.get_logger(__name__)


async def process_claim(
    *,
    container,
    service_name: str,
    worker_id: str,
    queue: str,
    claim: ToolRunJobClaim,
    lease_ttl: timedelta,
    heartbeat_interval: float,
    adopt_missing_backoff_seconds: int,
    runner: ToolRunnerProtocol,
    runner_adoption: ToolRunnerAdoptionProtocol,
    run_inputs: RunInputStorageProtocol,
    ui_policy_provider: UiPolicyProviderProtocol,
    backend_actions_provider: BackendActionProviderProtocol,
    ui_normalizer: UiPayloadNormalizerProtocol,
    clock: ClockProtocol,
    id_generator: IdGeneratorProtocol,
    sleeper: SleeperProtocol,
) -> None:
    job = claim.job
    started_at = time.monotonic()

    logger.info(
        "Job claimed",
        queue=queue,
        job_id=str(job.id),
        run_id=str(job.run_id),
        is_adoption=claim.is_adoption,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        locked_by=job.locked_by,
        locked_until=None if job.locked_until is None else job.locked_until.isoformat(),
    )

    try:
        ctx = await load_execution_context(
            container=container,
            run_id=job.run_id,
            ui_policy_provider=ui_policy_provider,
            backend_actions_provider=backend_actions_provider,
            id_generator=id_generator,
        )
    except DomainError:
        logger.exception(
            "Failed to load execution context",
            run_id=str(job.run_id),
            job_id=str(job.id),
            worker_id=worker_id,
        )
        await finalize_job_as_failed(
            container=container,
            worker_id=worker_id,
            run_id=job.run_id,
            job_id=job.id,
            error_summary="Execution failed (internal error).",
            clock=clock,
        )
        return

    stop_heartbeat = asyncio.Event()
    heartbeat_task = asyncio.create_task(
        heartbeat_loop(
            container=container,
            sleeper=sleeper,
            clock=clock,
            job_id=job.id,
            worker_id=worker_id,
            lease_ttl=lease_ttl,
            interval_seconds=heartbeat_interval,
            stop_event=stop_heartbeat,
        )
    )

    try:
        tracer = get_tracer(service_name)
        with trace_operation(
            tracer,
            "execution_worker.process_claim",
            {
                "job.id": str(job.id),
                "run.id": str(job.run_id),
                "queue": queue,
                "worker.id": worker_id,
                "job.is_adoption": str(claim.is_adoption),
            },
        ) as span:
            outcome = await run_execution_attempt(
                claim_is_adoption=claim.is_adoption,
                job=job,
                ctx=ctx,
                runner=runner,
                runner_adoption=runner_adoption,
                run_inputs=run_inputs,
                queue=queue,
                worker_id=worker_id,
            )
            if outcome is None:
                await requeue_missing_adoptable_container(
                    container=container,
                    run=ctx.run,
                    now=clock.now(),
                    backoff_seconds=adopt_missing_backoff_seconds,
                    worker_id=worker_id,
                )
                span.add_event("adopt_missing_container")
                return

            finish_now = clock.now()
            normalization_result = normalize_ui_payload(
                ui_normalizer=ui_normalizer,
                raw_result=outcome.raw_result,
                backend_actions=ctx.backend_actions,
                policy=ctx.policy,
                run_id=job.run_id,
            )

            finished_run = finish_run(
                run=ctx.run,
                status=outcome.execution_result.status,
                now=finish_now,
                stdout=outcome.execution_result.stdout,
                stderr=outcome.execution_result.stderr,
                artifacts_manifest=outcome.execution_result.artifacts_manifest.model_dump(),
                error_summary=outcome.raw_result.error_summary,
                ui_payload=normalization_result.ui_payload,
            )
            finished_job = mark_job_finished(
                job=job,
                status=finished_run.status,
                now=finish_now,
            )

            updated = await finalize_job(
                container=container,
                worker_id=worker_id,
                run=finished_run,
                job=finished_job,
                state_update=normalization_result.state_update,
                id_generator=id_generator,
            )
            if updated:
                await run_inputs.delete(run_id=job.run_id)

            span.set_attribute("run.status", finished_run.status.value)
            span.set_attribute("job.finalized", str(updated))
            span.set_attribute("job.duration_seconds", round(time.monotonic() - started_at, 6))
    finally:
        stop_heartbeat.set()
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
