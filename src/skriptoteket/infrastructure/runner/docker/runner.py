from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from uuid import UUID

import structlog
from pydantic import JsonValue

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.execution import ToolExecutionResult
from skriptoteket.domain.scripting.input_files import normalize_input_files
from skriptoteket.domain.scripting.models import RunContext, RunStatus, ToolVersion
from skriptoteket.domain.scripting.ui.contract_v2 import ToolUiContractV2Result
from skriptoteket.infrastructure.runner.capacity import RunnerCapacityLimiter
from skriptoteket.infrastructure.runner.result_contract import parse_runner_result_json
from skriptoteket.observability.tracing import get_tracer, trace_operation
from skriptoteket.protocols.runner import ArtifactManagerProtocol, ToolRunnerProtocol

from .client_adapter import DockerClientAdapter
from .container_io import (
    fetch_result_json_bytes,
    fetch_stdout_stderr,
    store_output_archive,
    store_output_archive_safely,
    truncate_utf8_str,
)
from .errors import raise_docker_client_unavailable
from .protocols import DockerClientProtocol, DockerContainerProtocol, DockerVolumeProtocol
from .workdir_archive import build_workdir_archive

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class DockerRunnerLimits:
    cpu_limit: float
    memory_limit: str
    pids_limit: int
    tmpfs_tmp: str


class DockerToolRunner(ToolRunnerProtocol):
    def __init__(
        self,
        *,
        runner_image: str,
        sandbox_timeout_seconds: int,
        production_timeout_seconds: int,
        limits: DockerRunnerLimits,
        output_max_stdout_bytes: int,
        output_max_stderr_bytes: int,
        output_max_error_summary_bytes: int,
        capacity: RunnerCapacityLimiter,
        artifacts: ArtifactManagerProtocol,
    ) -> None:
        self._runner_image = runner_image
        self._sandbox_timeout_seconds = sandbox_timeout_seconds
        self._production_timeout_seconds = production_timeout_seconds
        self._limits = limits
        self._output_max_stdout_bytes = output_max_stdout_bytes
        self._output_max_stderr_bytes = output_max_stderr_bytes
        self._output_max_error_summary_bytes = output_max_error_summary_bytes
        self._capacity = capacity
        self._artifacts = artifacts

    async def execute(
        self,
        *,
        run_id: UUID,
        version: ToolVersion,
        context: RunContext,
        input_files: list[tuple[str, bytes]],
        input_values: dict[str, JsonValue],
        memory_json: bytes,
        action_payload: dict[str, JsonValue] | None,
    ) -> ToolExecutionResult:
        if not await self._capacity.try_acquire():
            logger.warning(
                "Runner at capacity",
                run_id=str(run_id),
                tool_id=str(version.tool_id),
                tool_version_id=str(version.id),
                context=context.value,
            )
            raise DomainError(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Runner is at capacity; retry.",
            )

        try:
            return await asyncio.to_thread(
                self._execute_sync,
                run_id=run_id,
                version=version,
                context=context,
                input_files=input_files,
                input_values=input_values,
                memory_json=memory_json,
                action_payload=action_payload,
            )
        finally:
            await self._capacity.release()

    def _execute_sync(
        self,
        *,
        run_id: UUID,
        version: ToolVersion,
        context: RunContext,
        input_files: list[tuple[str, bytes]],
        input_values: dict[str, JsonValue],
        memory_json: bytes,
        action_payload: dict[str, JsonValue] | None,
    ) -> ToolExecutionResult:
        import docker
        from docker.errors import DockerException
        from requests.exceptions import ReadTimeout

        tracer = get_tracer("skriptoteket")
        start_time = time.monotonic()
        timeout_seconds = (
            self._sandbox_timeout_seconds
            if context is RunContext.SANDBOX
            else self._production_timeout_seconds
        )
        normalized_input_files = (
            normalize_input_files(input_files=input_files)[0] if input_files else []
        )
        input_manifest = {
            "files": [
                {"name": name, "path": f"/work/input/{name}", "bytes": len(content)}
                for name, content in normalized_input_files
            ]
        }
        input_manifest_json = json.dumps(input_manifest, ensure_ascii=False, separators=(",", ":"))
        inputs_json = json.dumps(input_values, ensure_ascii=False, separators=(",", ":"))

        logger.info(
            "Runner execution start",
            run_id=str(run_id),
            tool_id=str(version.tool_id),
            tool_version_id=str(version.id),
            context=context.value,
            timeout_seconds=timeout_seconds,
            input_files_count=len(normalized_input_files),
            cpu_limit=self._limits.cpu_limit,
            memory_limit=self._limits.memory_limit,
            pids_limit=self._limits.pids_limit,
        )

        nano_cpus = int(self._limits.cpu_limit * 1_000_000_000)
        env: dict[str, str] = {
            "HOME": "/tmp/home",
            "XDG_CACHE_HOME": "/tmp/home/.cache",
            "SKRIPTOTEKET_SCRIPT_PATH": "/work/script.py",
            "SKRIPTOTEKET_ENTRYPOINT": version.entrypoint,
            "SKRIPTOTEKET_INPUT_DIR": "/work/input",
            "SKRIPTOTEKET_INPUT_MANIFEST": input_manifest_json,
            "SKRIPTOTEKET_INPUTS": inputs_json,
            "SKRIPTOTEKET_MEMORY_PATH": "/work/memory.json",
            "SKRIPTOTEKET_OUTPUT_DIR": "/work/output",
            "SKRIPTOTEKET_RESULT_PATH": "/work/result.json",
        }
        if action_payload is not None:
            try:
                env["SKRIPTOTEKET_ACTION"] = json.dumps(
                    action_payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            except TypeError as exc:
                raise DomainError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Failed to encode action payload as JSON.",
                ) from exc

        client: DockerClientProtocol
        container: DockerContainerProtocol | None = None
        work_volume: DockerVolumeProtocol | None = None

        try:
            client = DockerClientAdapter(docker.from_env())
        except DockerException as exc:
            raise_docker_client_unavailable(exc=exc)

        try:
            with trace_operation(
                tracer,
                "docker_runner.execute",
                {
                    "run.id": str(run_id),
                    "tool.id": str(version.tool_id),
                    "version.id": str(version.id),
                    "run.context": context.value,
                },
            ) as span:
                work_volume = client.volumes.create(
                    labels={
                        "skriptoteket.run_id": str(run_id),
                        "skriptoteket.tool_version_id": str(version.id),
                        "skriptoteket.tool_id": str(version.tool_id),
                    }
                )
                span.add_event("volume_created")

                workdir_tar = build_workdir_archive(
                    version=version,
                    input_files=normalized_input_files,
                    memory_json=memory_json,
                )

                container = client.containers.create(
                    image=self._runner_image,
                    environment=env,
                    command=[
                        "sh",
                        "-lc",
                        "set -euo pipefail; mkdir -p /tmp/home; "
                        "/app/.venv/bin/python /runner/_runner.py",
                    ],
                    working_dir="/app",
                    network_mode="none",
                    user="runner",
                    cap_drop=["ALL"],
                    pids_limit=self._limits.pids_limit,
                    read_only=True,
                    tmpfs={
                        "/tmp": self._limits.tmpfs_tmp,
                    },
                    volumes={work_volume.name: {"bind": "/work", "mode": "rw"}},
                    mem_limit=self._limits.memory_limit,
                    nano_cpus=nano_cpus,
                    labels={
                        "skriptoteket.run_id": str(run_id),
                        "skriptoteket.tool_version_id": str(version.id),
                        "skriptoteket.tool_id": str(version.tool_id),
                    },
                )

                container.put_archive(path="/work", data=workdir_tar)
                container.start()
                span.add_event("container_started")

                timed_out = False
                try:
                    container.wait(timeout=timeout_seconds)
                except ReadTimeout:
                    timed_out = True
                    try:
                        container.kill()
                    except DockerException:
                        pass
                    try:
                        container.wait(timeout=10)
                    except ReadTimeout:
                        pass

                span.add_event("container_finished", {"timed_out": str(timed_out)})

                stdout, stderr = fetch_stdout_stderr(
                    container=container,
                    max_stdout_bytes=self._output_max_stdout_bytes,
                    max_stderr_bytes=self._output_max_stderr_bytes,
                )

                result_json_bytes = fetch_result_json_bytes(container=container)

                if timed_out:
                    artifacts_manifest = store_output_archive_safely(
                        container=container,
                        run_id=run_id,
                        artifacts=self._artifacts,
                    )
                    span.add_event(
                        "artifacts_extracted", {"count": str(len(artifacts_manifest.artifacts))}
                    )
                    span.set_attribute("run.status", RunStatus.TIMED_OUT.value)
                    span.set_attribute(
                        "run.duration_seconds", round(time.monotonic() - start_time, 6)
                    )
                    span.set_attribute("run.artifacts_count", len(artifacts_manifest.artifacts))

                    logger.warning(
                        "Runner execution timed out",
                        run_id=str(run_id),
                        tool_id=str(version.tool_id),
                        tool_version_id=str(version.id),
                        context=context.value,
                        timeout_seconds=timeout_seconds,
                        duration_seconds=round(time.monotonic() - start_time, 6),
                    )

                    timed_out_error_summary = truncate_utf8_str(
                        value="Execution timed out.",
                        max_bytes=self._output_max_error_summary_bytes,
                    )
                    ui_result = ToolUiContractV2Result(
                        status="timed_out",
                        error_summary=timed_out_error_summary,
                        outputs=[],
                        next_actions=[],
                        state=None,
                        artifacts=[],
                    )
                    return ToolExecutionResult(
                        status=RunStatus.TIMED_OUT,
                        stdout=stdout,
                        stderr=stderr,
                        ui_result=ui_result,
                        artifacts_manifest=artifacts_manifest,
                    )

                if result_json_bytes is None:
                    artifacts_manifest = store_output_archive_safely(
                        container=container,
                        run_id=run_id,
                        artifacts=self._artifacts,
                    )
                    logger.warning(
                        "Runner contract violation (missing result.json)",
                        run_id=str(run_id),
                        tool_id=str(version.tool_id),
                        tool_version_id=str(version.id),
                        context=context.value,
                        duration_seconds=round(time.monotonic() - start_time, 6),
                    )
                    raise DomainError(
                        code=ErrorCode.INTERNAL_ERROR,
                        message="Execution failed (runner contract violation).",
                        details={
                            "reason": "missing result.json",
                            "stdout": stdout,
                            "stderr": stderr,
                            "artifacts_manifest": artifacts_manifest.model_dump(),
                        },
                    )

                try:
                    runner_payload = parse_runner_result_json(result_json_bytes=result_json_bytes)
                except DomainError as exc:
                    artifacts_manifest = store_output_archive_safely(
                        container=container,
                        run_id=run_id,
                        artifacts=self._artifacts,
                    )
                    logger.warning(
                        "Runner contract violation (invalid result.json)",
                        run_id=str(run_id),
                        tool_id=str(version.tool_id),
                        tool_version_id=str(version.id),
                        context=context.value,
                        duration_seconds=round(time.monotonic() - start_time, 6),
                    )
                    raise DomainError(
                        code=ErrorCode.INTERNAL_ERROR,
                        message="Execution failed (runner contract violation).",
                        details={
                            "reason": "invalid result.json",
                            "validation": exc.details,
                            "stdout": stdout,
                            "stderr": stderr,
                            "artifacts_manifest": artifacts_manifest.model_dump(),
                        },
                    ) from exc

                status = RunStatus(runner_payload.status)
                runner_error_summary: str | None = (
                    None
                    if runner_payload.error_summary is None
                    else truncate_utf8_str(
                        value=runner_payload.error_summary,
                        max_bytes=self._output_max_error_summary_bytes,
                    )
                )
                ui_result = (
                    runner_payload
                    if runner_payload.error_summary == runner_error_summary
                    else runner_payload.model_copy(update={"error_summary": runner_error_summary})
                )

                try:
                    artifacts_manifest = store_output_archive(
                        container=container,
                        run_id=run_id,
                        reported_artifacts=runner_payload.artifacts,
                        artifacts=self._artifacts,
                    )
                except DomainError:
                    logger.warning(
                        "Artifact extraction violation",
                        run_id=str(run_id),
                        tool_id=str(version.tool_id),
                        tool_version_id=str(version.id),
                        context=context.value,
                        duration_seconds=round(time.monotonic() - start_time, 6),
                    )
                    raise DomainError(
                        code=ErrorCode.INTERNAL_ERROR,
                        message="Execution failed (artifact extraction violation).",
                        details={
                            "stdout": stdout,
                            "stderr": stderr,
                        },
                    )

                span.add_event(
                    "artifacts_extracted", {"count": str(len(artifacts_manifest.artifacts))}
                )
                span.set_attribute("run.status", status.value)
                span.set_attribute("run.duration_seconds", round(time.monotonic() - start_time, 6))
                span.set_attribute("run.artifacts_count", len(artifacts_manifest.artifacts))

                logger.info(
                    "Runner execution finished",
                    run_id=str(run_id),
                    tool_id=str(version.tool_id),
                    tool_version_id=str(version.id),
                    context=context.value,
                    status=status.value,
                    duration_seconds=round(time.monotonic() - start_time, 6),
                    artifacts_count=len(artifacts_manifest.artifacts),
                )
                return ToolExecutionResult(
                    status=status,
                    stdout=stdout,
                    stderr=stderr,
                    ui_result=ui_result,
                    artifacts_manifest=artifacts_manifest,
                )

        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except DockerException:
                    pass
            if work_volume is not None:
                try:
                    work_volume.remove(force=True)
                except DockerException:
                    pass
            if client is not None:
                try:
                    client.close()
                except AttributeError:
                    pass
