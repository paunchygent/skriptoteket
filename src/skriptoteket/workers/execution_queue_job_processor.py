from __future__ import annotations

import asyncio
import time
from datetime import timedelta

import structlog

from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.domain.scripting.execution import ToolExecutionResult
from skriptoteket.domain.scripting.models import RunStatus
from skriptoteket.domain.scripting.tool_run_jobs import mark_job_finished
from skriptoteket.domain.scripting.tool_runs import finish_run
from skriptoteket.domain.scripting.ui.contract_v2 import ToolUiContractV2Result, UiFormAction
from skriptoteket.domain.scripting.ui.normalization import UiNormalizationResult
from skriptoteket.domain.scripting.ui.policy import UiPolicy
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
    heartbeat_once,
    load_execution_context,
    requeue_missing_adoptable_container,
)

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
        _heartbeat_loop(
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
            execution_result: ToolExecutionResult | None = None
            raw_result: ToolUiContractV2Result | None = None

            try:
                compile(ctx.version.source_code, "<tool_version>", "exec")

                if claim.is_adoption:
                    execution_result = await runner_adoption.try_adopt(
                        run_id=job.run_id,
                        version=ctx.version,
                        context=ctx.run.context,
                    )
                    if execution_result is None:
                        if job.attempts >= job.max_attempts:
                            error_summary = "Execution failed (missing runner container)."
                            raw_result = ToolUiContractV2Result(
                                status="failed",
                                error_summary=error_summary,
                                outputs=[],
                                next_actions=[],
                                state=None,
                                artifacts=[],
                            )
                            execution_result = ToolExecutionResult(
                                status=RunStatus.FAILED,
                                stdout="",
                                stderr="",
                                ui_result=raw_result,
                                artifacts_manifest=ArtifactsManifest(artifacts=[]),
                            )
                        else:
                            await requeue_missing_adoptable_container(
                                container=container,
                                run=ctx.run,
                                now=clock.now(),
                                backoff_seconds=adopt_missing_backoff_seconds,
                                worker_id=worker_id,
                            )
                            span.add_event("adopt_missing_container")
                            return
                else:
                    input_files = await run_inputs.get(run_id=job.run_id)
                    execution_result = await runner.execute(
                        run_id=job.run_id,
                        version=ctx.version,
                        context=ctx.run.context,
                        input_files=input_files,
                        input_values=ctx.run.input_values,
                        memory_json=ctx.memory_json,
                        action_payload=None,
                    )
            except SyntaxError as exc:
                error_summary = _format_syntax_error(exc)
                raw_result = ToolUiContractV2Result(
                    status="failed",
                    error_summary=error_summary,
                    outputs=[],
                    next_actions=[],
                    state=None,
                    artifacts=[],
                )
                execution_result = ToolExecutionResult(
                    status=RunStatus.FAILED,
                    stdout="",
                    stderr="",
                    ui_result=raw_result,
                    artifacts_manifest=ArtifactsManifest(artifacts=[]),
                )
            except DomainError as exc:
                raw_result = ToolUiContractV2Result(
                    status="failed",
                    error_summary=exc.message,
                    outputs=[],
                    next_actions=[],
                    state=None,
                    artifacts=[],
                )
                stdout = ""
                stderr = ""
                artifacts_manifest = ArtifactsManifest(artifacts=[])
                stdout_candidate = exc.details.get("stdout")
                if isinstance(stdout_candidate, str):
                    stdout = stdout_candidate
                stderr_candidate = exc.details.get("stderr")
                if isinstance(stderr_candidate, str):
                    stderr = stderr_candidate
                artifacts_candidate = exc.details.get("artifacts_manifest")
                if isinstance(artifacts_candidate, dict):
                    try:
                        artifacts_manifest = ArtifactsManifest.model_validate(artifacts_candidate)
                    except ValueError:
                        artifacts_manifest = ArtifactsManifest(artifacts=[])
                execution_result = ToolExecutionResult(
                    status=RunStatus.FAILED,
                    stdout=stdout,
                    stderr=stderr,
                    ui_result=raw_result,
                    artifacts_manifest=artifacts_manifest,
                )
            except Exception:  # noqa: BLE001
                logger.exception(
                    "Job execution failed (unexpected exception)",
                    queue=queue,
                    job_id=str(job.id),
                    run_id=str(job.run_id),
                    worker_id=worker_id,
                )
                raw_result = ToolUiContractV2Result(
                    status="failed",
                    error_summary="Execution failed (internal error).",
                    outputs=[],
                    next_actions=[],
                    state=None,
                    artifacts=[],
                )
                execution_result = ToolExecutionResult(
                    status=RunStatus.FAILED,
                    stdout="",
                    stderr="",
                    ui_result=raw_result,
                    artifacts_manifest=ArtifactsManifest(artifacts=[]),
                )

            finish_now = clock.now()
            raw_result = (
                execution_result.ui_result
                if execution_result is not None
                else raw_result
                if raw_result is not None
                else ToolUiContractV2Result(
                    status="failed",
                    error_summary=None,
                    outputs=[],
                    next_actions=[],
                    state=None,
                    artifacts=[],
                )
            )
            normalization_result = _normalize_ui_payload(
                ui_normalizer=ui_normalizer,
                raw_result=raw_result,
                backend_actions=ctx.backend_actions,
                policy=ctx.policy,
                run_id=job.run_id,
            )

            finished_run = finish_run(
                run=ctx.run,
                status=execution_result.status
                if execution_result is not None
                else RunStatus.FAILED,
                now=finish_now,
                stdout=execution_result.stdout if execution_result is not None else "",
                stderr=execution_result.stderr if execution_result is not None else "",
                artifacts_manifest=(
                    execution_result.artifacts_manifest.model_dump()
                    if execution_result is not None
                    else {}
                ),
                error_summary=raw_result.error_summary,
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
                normalized_state=normalization_result.state,
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


async def _heartbeat_loop(
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


def _normalize_ui_payload(
    *,
    ui_normalizer: UiPayloadNormalizerProtocol,
    raw_result: ToolUiContractV2Result,
    backend_actions: list[UiFormAction],
    policy: UiPolicy,
    run_id,
) -> UiNormalizationResult:
    try:
        return ui_normalizer.normalize(
            raw_result=raw_result,
            backend_actions=backend_actions,
            policy=policy,
        )
    except DomainError:
        logger.exception(
            "UI payload normalization failed",
            run_id=str(run_id),
        )
        return ui_normalizer.normalize(
            raw_result=ToolUiContractV2Result(
                status="failed",
                error_summary="Execution failed (ui_payload normalization error).",
                outputs=[],
                next_actions=[],
                state=None,
                artifacts=[],
            ),
            backend_actions=backend_actions,
            policy=policy,
        )


def _format_syntax_error(exc: SyntaxError) -> str:
    parts: list[str] = [f"SyntaxError: {exc.msg}"]

    location_parts: list[str] = []
    if exc.lineno is not None:
        location_parts.append(f"line {exc.lineno}")
    if exc.offset is not None:
        location_parts.append(f"col {exc.offset}")
    if location_parts:
        parts[0] = f"{parts[0]} ({', '.join(location_parts)})"

    if exc.text:
        code_line = exc.text.rstrip("\n")
        parts.append(code_line)
        if exc.offset is not None:
            caret_position = max(exc.offset - 1, 0)
            parts.append(" " * caret_position + "^")

    return "\n".join(parts)
