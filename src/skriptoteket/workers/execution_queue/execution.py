from dataclasses import dataclass

import structlog

from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.domain.scripting.execution import ToolExecutionResult
from skriptoteket.domain.scripting.models import RunStatus
from skriptoteket.domain.scripting.tool_run_jobs import ToolRunJob
from skriptoteket.domain.scripting.ui.contract_v2 import ToolUiContractV2Result
from skriptoteket.protocols.run_inputs import RunInputStorageProtocol
from skriptoteket.protocols.runner import ToolRunnerAdoptionProtocol, ToolRunnerProtocol
from skriptoteket.workers.execution_queue_job_db import JobExecutionContext

from .formatting import format_syntax_error

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ExecutionOutcome:
    execution_result: ToolExecutionResult
    raw_result: ToolUiContractV2Result


async def run_execution_attempt(
    *,
    claim_is_adoption: bool,
    job: ToolRunJob,
    ctx: JobExecutionContext,
    runner: ToolRunnerProtocol,
    runner_adoption: ToolRunnerAdoptionProtocol,
    run_inputs: RunInputStorageProtocol,
    queue: str,
    worker_id: str,
) -> ExecutionOutcome | None:
    execution_result: ToolExecutionResult | None = None
    raw_result: ToolUiContractV2Result | None = None

    try:
        compile(ctx.version.source_code, "<tool_version>", "exec")

        if claim_is_adoption:
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
                    return None
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
        error_summary = format_syntax_error(exc)
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

    if execution_result is None:
        execution_result = ToolExecutionResult(
            status=RunStatus.FAILED,
            stdout="",
            stderr="",
            ui_result=raw_result,
            artifacts_manifest=ArtifactsManifest(artifacts=[]),
        )

    return ExecutionOutcome(execution_result=execution_result, raw_result=raw_result)
