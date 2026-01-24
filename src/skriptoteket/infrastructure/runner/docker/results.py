from dataclasses import dataclass
from uuid import UUID

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.domain.scripting.execution import ToolExecutionResult
from skriptoteket.domain.scripting.models import RunStatus
from skriptoteket.domain.scripting.ui.contract_v2 import ToolUiContractV2Result
from skriptoteket.protocols.runner import ArtifactManagerProtocol

from .container_io import (
    fetch_result_json_bytes,
    fetch_stdout_stderr,
    store_output_archive_safely,
    truncate_utf8_str,
)


@dataclass(frozen=True, slots=True)
class ExecutionOutputs:
    stdout: str
    stderr: str
    result_json_bytes: bytes | None


def fetch_execution_outputs(
    *,
    container,
    max_stdout_bytes: int,
    max_stderr_bytes: int,
) -> ExecutionOutputs:
    stdout, stderr = fetch_stdout_stderr(
        container=container,
        max_stdout_bytes=max_stdout_bytes,
        max_stderr_bytes=max_stderr_bytes,
    )
    result_json_bytes = fetch_result_json_bytes(container=container)
    return ExecutionOutputs(
        stdout=stdout,
        stderr=stderr,
        result_json_bytes=result_json_bytes,
    )


def build_timed_out_result(
    *,
    container,
    run_id: UUID,
    artifacts: ArtifactManagerProtocol,
    stdout: str,
    stderr: str,
    output_max_error_summary_bytes: int,
) -> tuple[ToolExecutionResult, ArtifactsManifest]:
    artifacts_manifest = store_output_archive_safely(
        container=container,
        run_id=run_id,
        artifacts=artifacts,
    )
    timed_out_error_summary = truncate_utf8_str(
        value="Execution timed out.",
        max_bytes=output_max_error_summary_bytes,
    )
    ui_result = ToolUiContractV2Result(
        status="timed_out",
        error_summary=timed_out_error_summary,
        outputs=[],
        next_actions=[],
        state=None,
        artifacts=[],
    )
    return (
        ToolExecutionResult(
            status=RunStatus.TIMED_OUT,
            stdout=stdout,
            stderr=stderr,
            ui_result=ui_result,
            artifacts_manifest=artifacts_manifest,
        ),
        artifacts_manifest,
    )


def build_missing_result_error(
    *,
    container,
    run_id: UUID,
    artifacts: ArtifactManagerProtocol,
    stdout: str,
    stderr: str,
) -> DomainError:
    artifacts_manifest = store_output_archive_safely(
        container=container,
        run_id=run_id,
        artifacts=artifacts,
    )
    return DomainError(
        code=ErrorCode.INTERNAL_ERROR,
        message="Execution failed (runner contract violation).",
        details={
            "reason": "missing result.json",
            "stdout": stdout,
            "stderr": stderr,
            "artifacts_manifest": artifacts_manifest.model_dump(),
        },
    )
