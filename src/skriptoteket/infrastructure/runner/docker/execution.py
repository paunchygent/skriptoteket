import time
from uuid import UUID

import structlog
from pydantic import JsonValue

from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.scripting.execution import ToolExecutionResult
from skriptoteket.domain.scripting.models import RunContext, RunStatus, ToolVersion
from skriptoteket.observability.tracing import get_tracer, trace_operation
from skriptoteket.protocols.runner import ArtifactManagerProtocol

from .cleanup import close_client, remove_container, remove_volume
from .client_adapter import DockerClientAdapter
from .env import prepare_execution_inputs
from .errors import raise_docker_client_unavailable
from .limits import DockerRunnerLimits
from .protocols import DockerClientProtocol, DockerContainerProtocol, DockerVolumeProtocol
from .results import (
    build_missing_result_error,
    build_timed_out_result,
    fetch_execution_outputs,
    parse_runner_payload,
)
from .workdir_archive import build_workdir_archive

logger = structlog.get_logger(__name__)


def execute_sync(
    *,
    run_id: UUID,
    version: ToolVersion,
    context: RunContext,
    input_files: list[tuple[str, bytes]],
    input_values: dict[str, JsonValue],
    memory_json: bytes,
    action_payload: dict[str, JsonValue] | None,
    runner_image: str,
    sandbox_timeout_seconds: int,
    production_timeout_seconds: int,
    limits: DockerRunnerLimits,
    output_max_stdout_bytes: int,
    output_max_stderr_bytes: int,
    output_max_error_summary_bytes: int,
    artifacts: ArtifactManagerProtocol,
) -> ToolExecutionResult:
    import docker
    from docker.errors import DockerException
    from requests.exceptions import ReadTimeout

    tracer = get_tracer("skriptoteket")
    start_time = time.monotonic()
    timeout_seconds = (
        sandbox_timeout_seconds if context is RunContext.SANDBOX else production_timeout_seconds
    )
    inputs = prepare_execution_inputs(
        version=version,
        input_files=input_files,
        input_values=input_values,
        action_payload=action_payload,
    )

    logger.info(
        "Runner execution start",
        run_id=str(run_id),
        tool_id=str(version.tool_id),
        tool_version_id=str(version.id),
        context=context.value,
        timeout_seconds=timeout_seconds,
        input_files_count=len(inputs.normalized_input_files),
        cpu_limit=limits.cpu_limit,
        memory_limit=limits.memory_limit,
        pids_limit=limits.pids_limit,
    )

    nano_cpus = int(limits.cpu_limit * 1_000_000_000)

    client: DockerClientProtocol | None = None
    container: DockerContainerProtocol | None = None
    work_volume: DockerVolumeProtocol | None = None

    try:
        try:
            client = DockerClientAdapter(docker.from_env())
        except DockerException as exc:
            raise_docker_client_unavailable(exc=exc)

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
                input_files=inputs.normalized_input_files,
                memory_json=memory_json,
            )

            container = client.containers.create(
                image=runner_image,
                environment=inputs.env,
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
                pids_limit=limits.pids_limit,
                read_only=True,
                tmpfs={
                    "/tmp": limits.tmpfs_tmp,
                },
                volumes={work_volume.name: {"bind": "/work", "mode": "rw"}},
                mem_limit=limits.memory_limit,
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

            outputs = fetch_execution_outputs(
                container=container,
                max_stdout_bytes=output_max_stdout_bytes,
                max_stderr_bytes=output_max_stderr_bytes,
            )

            if timed_out:
                result, artifacts_manifest = build_timed_out_result(
                    container=container,
                    run_id=run_id,
                    artifacts=artifacts,
                    stdout=outputs.stdout,
                    stderr=outputs.stderr,
                    output_max_error_summary_bytes=output_max_error_summary_bytes,
                )
                span.add_event(
                    "artifacts_extracted",
                    {"count": str(len(artifacts_manifest.artifacts))},
                )
                span.set_attribute("run.status", RunStatus.TIMED_OUT.value)
                span.set_attribute("run.duration_seconds", round(time.monotonic() - start_time, 6))
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
                return result

            if outputs.result_json_bytes is None:
                error = build_missing_result_error(
                    container=container,
                    run_id=run_id,
                    artifacts=artifacts,
                    stdout=outputs.stdout,
                    stderr=outputs.stderr,
                )
                logger.warning(
                    "Runner contract violation (missing result.json)",
                    run_id=str(run_id),
                    tool_id=str(version.tool_id),
                    tool_version_id=str(version.id),
                    context=context.value,
                    duration_seconds=round(time.monotonic() - start_time, 6),
                )
                raise error

            try:
                status, ui_result, artifacts_manifest = parse_runner_payload(
                    container=container,
                    result_json_bytes=outputs.result_json_bytes,
                    run_id=run_id,
                    stdout=outputs.stdout,
                    stderr=outputs.stderr,
                    artifacts=artifacts,
                    output_max_error_summary_bytes=output_max_error_summary_bytes,
                )
            except DomainError as exc:
                if exc.details.get("reason") == "invalid result.json":
                    logger.warning(
                        "Runner contract violation (invalid result.json)",
                        run_id=str(run_id),
                        tool_id=str(version.tool_id),
                        tool_version_id=str(version.id),
                        context=context.value,
                        duration_seconds=round(time.monotonic() - start_time, 6),
                    )
                elif exc.message == "Execution failed (artifact extraction violation).":
                    logger.warning(
                        "Artifact extraction violation",
                        run_id=str(run_id),
                        tool_id=str(version.tool_id),
                        tool_version_id=str(version.id),
                        context=context.value,
                        duration_seconds=round(time.monotonic() - start_time, 6),
                    )
                raise

            span.add_event("artifacts_extracted", {"count": str(len(artifacts_manifest.artifacts))})
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
                stdout=outputs.stdout,
                stderr=outputs.stderr,
                ui_result=ui_result,
                artifacts_manifest=artifacts_manifest,
            )

    finally:
        remove_container(container, swallow_all=False)
        remove_volume(work_volume, swallow_all=False)
        close_client(client)
