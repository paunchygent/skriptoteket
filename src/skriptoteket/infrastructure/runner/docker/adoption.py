import time
from uuid import UUID

from skriptoteket.domain.scripting.execution import ToolExecutionResult
from skriptoteket.domain.scripting.models import RunContext, RunStatus, ToolVersion
from skriptoteket.observability.tracing import get_tracer, trace_operation
from skriptoteket.protocols.runner import ArtifactManagerProtocol

from .cleanup import close_client, remove_container, remove_run_volumes
from .client_adapter import DockerClientAdapter
from .protocols import DockerClientProtocol, DockerContainerProtocol
from .results import (
    build_missing_result_error,
    build_timed_out_result,
    fetch_execution_outputs,
    parse_runner_payload,
)


def try_adopt_sync(
    *,
    run_id: UUID,
    version: ToolVersion,
    context: RunContext,
    sandbox_timeout_seconds: int,
    production_timeout_seconds: int,
    output_max_stdout_bytes: int,
    output_max_stderr_bytes: int,
    output_max_error_summary_bytes: int,
    artifacts: ArtifactManagerProtocol,
) -> ToolExecutionResult | None:
    import docker
    from docker.errors import DockerException
    from requests.exceptions import ReadTimeout

    timeout_seconds = (
        sandbox_timeout_seconds if context is RunContext.SANDBOX else production_timeout_seconds
    )

    client: DockerClientProtocol | None = None
    container: DockerContainerProtocol | None = None

    try:
        client = DockerClientAdapter(docker.from_env())

        containers = client.containers.list(
            all=True,
            filters={"label": f"skriptoteket.run_id={run_id}"},
        )
        if not containers:
            return None

        for candidate in containers:
            try:
                candidate.reload()
            except DockerException:
                continue
            if candidate.status == "running":
                container = candidate
                break
        if container is None:
            container = containers[0]
            try:
                container.reload()
            except DockerException:
                pass

        if container.status == "created":
            try:
                container.remove(force=True)
            except DockerException:
                pass
            return None

        start_time = time.monotonic()
        tracer = get_tracer("skriptoteket")
        with trace_operation(
            tracer,
            "docker_runner.adopt",
            {
                "run.id": str(run_id),
                "tool.id": str(version.tool_id),
                "version.id": str(version.id),
                "run.context": context.value,
            },
        ) as span:
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
                span.set_attribute("run.status", RunStatus.TIMED_OUT.value)
                span.set_attribute("run.duration_seconds", round(time.monotonic() - start_time, 6))
                span.set_attribute("run.artifacts_count", len(artifacts_manifest.artifacts))
                return result

            if outputs.result_json_bytes is None:
                error = build_missing_result_error(
                    container=container,
                    run_id=run_id,
                    artifacts=artifacts,
                    stdout=outputs.stdout,
                    stderr=outputs.stderr,
                )
                raise error

            status, ui_result, artifacts_manifest = parse_runner_payload(
                container=container,
                result_json_bytes=outputs.result_json_bytes,
                run_id=run_id,
                stdout=outputs.stdout,
                stderr=outputs.stderr,
                artifacts=artifacts,
                output_max_error_summary_bytes=output_max_error_summary_bytes,
            )

            span.set_attribute("run.status", status.value)
            span.set_attribute("run.duration_seconds", round(time.monotonic() - start_time, 6))
            span.set_attribute("run.artifacts_count", len(artifacts_manifest.artifacts))
            return ToolExecutionResult(
                status=status,
                stdout=outputs.stdout,
                stderr=outputs.stderr,
                ui_result=ui_result,
                artifacts_manifest=artifacts_manifest,
            )
    finally:
        remove_container(container, swallow_all=True)
        remove_run_volumes(client=client, run_id=run_id)
        close_client(client)
