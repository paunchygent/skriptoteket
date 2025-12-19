from __future__ import annotations

import asyncio
import io
import tarfile
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Protocol
from uuid import UUID

import structlog

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.execution import (
    ArtifactsManifest,
    RunnerArtifact,
    ToolExecutionResult,
)
from skriptoteket.domain.scripting.models import RunContext, RunStatus, ToolVersion
from skriptoteket.infrastructure.runner.capacity import RunnerCapacityLimiter
from skriptoteket.infrastructure.runner.result_contract import parse_runner_result_json
from skriptoteket.protocols.runner import ArtifactManagerProtocol, ToolRunnerProtocol

logger = structlog.get_logger(__name__)


class DockerContainerProtocol(Protocol):
    def put_archive(self, *, path: str, data: bytes) -> bool: ...

    def start(self) -> None: ...

    def wait(self, *, timeout: int) -> object: ...

    def kill(self) -> None: ...

    def logs(self, *, stdout: bool, stderr: bool) -> bytes: ...

    def get_archive(self, *, path: str) -> tuple[Iterable[bytes], object]: ...

    def remove(self, *, force: bool) -> None: ...


class DockerVolumeProtocol(Protocol):
    @property
    def name(self) -> str: ...

    def remove(self, *, force: bool) -> None: ...


class DockerVolumesClientProtocol(Protocol):
    def create(self, *, labels: dict[str, str]) -> DockerVolumeProtocol: ...


class DockerContainersClientProtocol(Protocol):
    def create(
        self,
        *,
        image: str,
        environment: dict[str, str],
        command: list[str],
        working_dir: str,
        network_mode: str,
        user: str,
        cap_drop: list[str],
        pids_limit: int,
        read_only: bool,
        tmpfs: dict[str, str],
        volumes: dict[str, dict[str, str]],
        mem_limit: str,
        nano_cpus: int,
        labels: dict[str, str],
    ) -> DockerContainerProtocol: ...


class DockerClientProtocol(Protocol):
    volumes: DockerVolumesClientProtocol
    containers: DockerContainersClientProtocol

    def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class DockerRunnerLimits:
    cpu_limit: float
    memory_limit: str
    pids_limit: int
    tmpfs_tmp: str


def _truncate_utf8_bytes(*, data: bytes, max_bytes: int) -> str:
    if max_bytes <= 0:
        return ""
    if len(data) <= max_bytes:
        return data.decode("utf-8", errors="replace")
    return data[:max_bytes].decode("utf-8", errors="replace")


def _truncate_utf8_str(*, value: str, max_bytes: int) -> str:
    if max_bytes <= 0:
        return ""
    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return value
    return encoded[:max_bytes].decode("utf-8", errors="ignore")


def _build_workdir_archive(
    *, version: ToolVersion, input_filename: str, input_bytes: bytes
) -> bytes:
    safe_input_filename = _sanitize_input_filename(input_filename=input_filename)

    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        script_bytes = version.source_code.encode("utf-8")

        script_info = tarfile.TarInfo(name="script.py")
        script_info.size = len(script_bytes)
        script_info.mode = 0o644
        tar.addfile(script_info, io.BytesIO(script_bytes))

        input_dir_info = tarfile.TarInfo(name="input")
        input_dir_info.type = tarfile.DIRTYPE
        input_dir_info.mode = 0o755
        input_dir_info.size = 0
        tar.addfile(input_dir_info)

        input_path = f"input/{safe_input_filename}"
        input_info = tarfile.TarInfo(name=input_path)
        input_info.size = len(input_bytes)
        input_info.mode = 0o644
        tar.addfile(input_info, io.BytesIO(input_bytes))

    return tar_buffer.getvalue()


def _extract_first_file_from_tar_bytes(*, tar_bytes: bytes) -> bytes:
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:*") as tar:
        for member in tar:
            if not member.isreg():
                continue
            extracted = tar.extractfile(member)
            if extracted is None:
                continue
            with extracted:
                return extracted.read()
    raise RuntimeError("No file found in tar archive")


def _sanitize_input_filename(*, input_filename: str) -> str:
    normalized = input_filename.strip()
    if not normalized:
        raise DomainError(code=ErrorCode.VALIDATION_ERROR, message="input_filename is required")

    posix = PurePosixPath(normalized)
    if posix.is_absolute() or ".." in posix.parts or "/" in normalized or "\\" in normalized:
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR, message="input_filename must be a file name"
        )

    if len(normalized) > 255:
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="input_filename must be 255 characters or less",
        )

    return normalized


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
        output_max_html_bytes: int,
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
        self._output_max_html_bytes = output_max_html_bytes
        self._output_max_error_summary_bytes = output_max_error_summary_bytes
        self._capacity = capacity
        self._artifacts = artifacts

    async def execute(
        self,
        *,
        run_id: UUID,
        version: ToolVersion,
        context: RunContext,
        input_filename: str,
        input_bytes: bytes,
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
                input_filename=input_filename,
                input_bytes=input_bytes,
            )
        finally:
            await self._capacity.release()

    def _execute_sync(
        self,
        *,
        run_id: UUID,
        version: ToolVersion,
        context: RunContext,
        input_filename: str,
        input_bytes: bytes,
    ) -> ToolExecutionResult:
        import docker
        from docker.errors import DockerException, NotFound
        from requests.exceptions import ReadTimeout

        start_time = time.monotonic()
        timeout_seconds = (
            self._sandbox_timeout_seconds
            if context is RunContext.SANDBOX
            else self._production_timeout_seconds
        )

        safe_input_filename = _sanitize_input_filename(input_filename=input_filename)

        logger.info(
            "Runner execution start",
            run_id=str(run_id),
            tool_id=str(version.tool_id),
            tool_version_id=str(version.id),
            context=context.value,
            timeout_seconds=timeout_seconds,
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
            "SKRIPTOTEKET_INPUT_PATH": f"/work/input/{safe_input_filename}",
            "SKRIPTOTEKET_OUTPUT_DIR": "/work/output",
            "SKRIPTOTEKET_RESULT_PATH": "/work/result.json",
        }

        client = docker.from_env()
        container: DockerContainerProtocol | None = None
        work_volume: DockerVolumeProtocol | None = None

        try:
            work_volume = client.volumes.create(
                labels={
                    "skriptoteket.run_id": str(run_id),
                    "skriptoteket.tool_version_id": str(version.id),
                    "skriptoteket.tool_id": str(version.tool_id),
                }
            )

            workdir_tar = _build_workdir_archive(
                version=version,
                input_filename=safe_input_filename,
                input_bytes=input_bytes,
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

            stdout_raw = container.logs(stdout=True, stderr=False)
            stderr_raw = container.logs(stdout=False, stderr=True)

            stdout = _truncate_utf8_bytes(data=stdout_raw, max_bytes=self._output_max_stdout_bytes)
            stderr = _truncate_utf8_bytes(data=stderr_raw, max_bytes=self._output_max_stderr_bytes)

            result_json_bytes: bytes | None = None
            try:
                tar_stream, _ = container.get_archive(path="/work/result.json")
                result_json_bytes = _extract_first_file_from_tar_bytes(
                    tar_bytes=b"".join(tar_stream)
                )
            except (NotFound, DockerException, RuntimeError):
                result_json_bytes = None

            if timed_out:
                artifacts_manifest = self._store_output_archive_safely(
                    container=container, run_id=run_id
                )
                logger.warning(
                    "Runner execution timed out",
                    run_id=str(run_id),
                    tool_id=str(version.tool_id),
                    tool_version_id=str(version.id),
                    context=context.value,
                    timeout_seconds=timeout_seconds,
                    duration_seconds=round(time.monotonic() - start_time, 6),
                )

                return ToolExecutionResult(
                    status=RunStatus.TIMED_OUT,
                    stdout=stdout,
                    stderr=stderr,
                    html_output="",
                    error_summary=_truncate_utf8_str(
                        value="Execution timed out.",
                        max_bytes=self._output_max_error_summary_bytes,
                    ),
                    artifacts_manifest=artifacts_manifest,
                )

            if result_json_bytes is None:
                artifacts_manifest = self._store_output_archive_safely(
                    container=container, run_id=run_id
                )
                logger.warning(
                    "Runner contract violation (missing result.json)",
                    run_id=str(run_id),
                    tool_id=str(version.tool_id),
                    tool_version_id=str(version.id),
                    context=context.value,
                    duration_seconds=round(time.monotonic() - start_time, 6),
                )
                return ToolExecutionResult(
                    status=RunStatus.FAILED,
                    stdout=stdout,
                    stderr=stderr,
                    html_output="",
                    error_summary=_truncate_utf8_str(
                        value="Execution failed (runner contract violation).",
                        max_bytes=self._output_max_error_summary_bytes,
                    ),
                    artifacts_manifest=artifacts_manifest,
                )

            try:
                runner_payload = parse_runner_result_json(result_json_bytes=result_json_bytes)
            except DomainError:
                artifacts_manifest = self._store_output_archive_safely(
                    container=container, run_id=run_id
                )
                logger.warning(
                    "Runner contract violation (invalid result.json)",
                    run_id=str(run_id),
                    tool_id=str(version.tool_id),
                    tool_version_id=str(version.id),
                    context=context.value,
                    duration_seconds=round(time.monotonic() - start_time, 6),
                )
                return ToolExecutionResult(
                    status=RunStatus.FAILED,
                    stdout=stdout,
                    stderr=stderr,
                    html_output="",
                    error_summary=_truncate_utf8_str(
                        value="Execution failed (runner contract violation).",
                        max_bytes=self._output_max_error_summary_bytes,
                    ),
                    artifacts_manifest=artifacts_manifest,
                )

            status = RunStatus(runner_payload.status)
            html_output = _truncate_utf8_str(
                value=runner_payload.html_output,
                max_bytes=self._output_max_html_bytes,
            )
            error_summary = (
                None
                if runner_payload.error_summary is None
                else _truncate_utf8_str(
                    value=runner_payload.error_summary,
                    max_bytes=self._output_max_error_summary_bytes,
                )
            )

            try:
                artifacts_manifest = self._store_output_archive(
                    container=container,
                    run_id=run_id,
                    reported_artifacts=runner_payload.artifacts,
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
                return ToolExecutionResult(
                    status=RunStatus.FAILED,
                    stdout=stdout,
                    stderr=stderr,
                    html_output="",
                    error_summary=_truncate_utf8_str(
                        value="Execution failed (artifact extraction violation).",
                        max_bytes=self._output_max_error_summary_bytes,
                    ),
                    artifacts_manifest=ArtifactsManifest(artifacts=[]),
                )

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
                html_output=html_output,
                error_summary=error_summary,
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
            try:
                client.close()
            except AttributeError:
                pass

    def _store_output_archive(
        self,
        *,
        container: DockerContainerProtocol,
        run_id: UUID,
        reported_artifacts: list[RunnerArtifact],
    ) -> ArtifactsManifest:
        from docker.errors import DockerException, NotFound

        try:
            tar_stream, _ = container.get_archive(path="/work/output")
            return self._artifacts.store_output_archive(
                run_id=run_id,
                output_archive=tar_stream,
                reported_artifacts=reported_artifacts,
            )
        except (NotFound, DockerException):
            return ArtifactsManifest(artifacts=[])

    def _store_output_archive_safely(
        self,
        *,
        container: DockerContainerProtocol,
        run_id: UUID,
    ) -> ArtifactsManifest:
        try:
            return self._store_output_archive(
                container=container,
                run_id=run_id,
                reported_artifacts=[],
            )
        except DomainError:
            return ArtifactsManifest(artifacts=[])
