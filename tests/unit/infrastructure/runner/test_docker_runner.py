from __future__ import annotations

import io
import json
import tarfile
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from docker.errors import NotFound
from requests.exceptions import ReadTimeout

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.domain.scripting.models import (
    RunContext,
    RunStatus,
    ToolVersion,
    VersionState,
    compute_content_hash,
)
from skriptoteket.infrastructure.runner.capacity import RunnerCapacityLimiter
from skriptoteket.infrastructure.runner.docker_runner import (
    DockerRunnerLimits,
    DockerToolRunner,
)
from skriptoteket.protocols.runner import ArtifactManagerProtocol


def create_result_tar(
    *,
    status: str,
    outputs: list[dict[str, object]],
    error_summary: str | None = None,
    next_actions: list[dict[str, object]] | None = None,
    state: dict[str, object] | None = None,
    artifacts: list[dict[str, object]] | None = None,
    contract_version: int = 2,
) -> bytes:
    payload = {
        "contract_version": contract_version,
        "status": status,
        "error_summary": error_summary,
        "outputs": outputs,
        "next_actions": next_actions or [],
        "state": state,
        "artifacts": artifacts or [],
    }
    result_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        info = tarfile.TarInfo(name="result.json")
        info.size = len(result_bytes)
        tar.addfile(info, io.BytesIO(result_bytes))

    return tar_buffer.getvalue()


@pytest.fixture
def tool_version(now: datetime) -> ToolVersion:
    source_code = "def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>Hi</p>'\n"
    entrypoint = "run_tool"
    return ToolVersion(
        id=uuid4(),
        tool_id=uuid4(),
        version_number=1,
        state=VersionState.DRAFT,
        source_code=source_code,
        entrypoint=entrypoint,
        content_hash=compute_content_hash(entrypoint=entrypoint, source_code=source_code),
        derived_from_version_id=None,
        created_by_user_id=uuid4(),
        created_at=now,
        submitted_for_review_by_user_id=None,
        submitted_for_review_at=None,
        reviewed_by_user_id=None,
        reviewed_at=None,
        published_by_user_id=None,
        published_at=None,
        change_summary=None,
        review_note=None,
    )


@pytest.fixture
def mock_capacity() -> MagicMock:
    capacity = MagicMock(spec=RunnerCapacityLimiter)
    capacity.try_acquire = AsyncMock(return_value=True)
    capacity.release = AsyncMock()
    return capacity


@pytest.fixture
def mock_artifacts() -> MagicMock:
    artifacts = MagicMock(spec=ArtifactManagerProtocol)
    artifacts.store_output_archive.return_value = ArtifactsManifest(artifacts=[])
    return artifacts


@pytest.fixture
def runner(mock_capacity: MagicMock, mock_artifacts: MagicMock) -> DockerToolRunner:
    limits = DockerRunnerLimits(
        cpu_limit=1.0,
        memory_limit="256m",
        pids_limit=128,
        tmpfs_tmp="size=64m",
    )
    return DockerToolRunner(
        runner_image="skriptoteket-runner:unit-test",
        sandbox_timeout_seconds=30,
        production_timeout_seconds=60,
        limits=limits,
        output_max_stdout_bytes=2048,
        output_max_stderr_bytes=2048,
        output_max_error_summary_bytes=2048,
        capacity=mock_capacity,
        artifacts=mock_artifacts,
    )


@pytest.fixture
def mock_docker_client(monkeypatch) -> MagicMock:
    import docker

    mocked_from_env = MagicMock(name="from_env")
    mocked_from_env.return_value = MagicMock()
    monkeypatch.setattr(docker, "from_env", mocked_from_env)
    return mocked_from_env


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_success(
    runner: DockerToolRunner,
    mock_docker_client: MagicMock,
    tool_version: ToolVersion,
    mock_capacity: MagicMock,
    mock_artifacts: MagicMock,
) -> None:
    client_instance = mock_docker_client.return_value

    volume = MagicMock()
    volume.name = "work-volume"
    client_instance.volumes.create.return_value = volume

    container = MagicMock()
    client_instance.containers.create.return_value = container

    container.logs.side_effect = [b"stdout", b"stderr"]
    container.wait.return_value = {"StatusCode": 0}

    result_tar = create_result_tar(
        status="succeeded",
        outputs=[{"kind": "html_sandboxed", "html": "<p>Hi</p>"}],
    )

    def get_archive_side_effect(*, path: str):
        if path == "/work/result.json":
            return [result_tar], {}
        if path == "/work/output":
            return [b"tar_stream"], {}
        raise NotFound("Not found")

    container.get_archive.side_effect = get_archive_side_effect

    result = await runner.execute(
        run_id=uuid4(),
        version=tool_version,
        context=RunContext.SANDBOX,
        input_files=[("input.txt", b"input")],
    )

    assert result.status is RunStatus.SUCCEEDED
    assert result.stdout == "stdout"
    assert result.stderr == "stderr"
    assert result.ui_result.error_summary is None
    assert result.ui_result.outputs[0].kind == "html_sandboxed"
    mock_artifacts.store_output_archive.assert_called_once()
    mock_capacity.try_acquire.assert_awaited_once()
    mock_capacity.release.assert_awaited_once()

    env = client_instance.containers.create.call_args.kwargs["environment"]
    assert env["SKRIPTOTEKET_INPUT_PATH"] == "/work/input/input.txt"
    manifest = json.loads(env["SKRIPTOTEKET_INPUT_MANIFEST"])
    assert manifest == {
        "files": [{"name": "input.txt", "path": "/work/input/input.txt", "bytes": 5}]
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_missing_result_json_returns_failed(
    runner: DockerToolRunner,
    mock_docker_client: MagicMock,
    tool_version: ToolVersion,
) -> None:
    client_instance = mock_docker_client.return_value

    volume = MagicMock()
    volume.name = "work-volume"
    client_instance.volumes.create.return_value = volume

    container = MagicMock()
    client_instance.containers.create.return_value = container
    container.logs.side_effect = [b"stdout", b"stderr"]
    container.wait.return_value = {"StatusCode": 0}
    container.get_archive.side_effect = NotFound("Not found")

    with pytest.raises(DomainError) as exc_info:
        await runner.execute(
            run_id=uuid4(),
            version=tool_version,
            context=RunContext.SANDBOX,
            input_files=[("input.txt", b"input")],
        )

    assert exc_info.value.code is ErrorCode.INTERNAL_ERROR
    assert exc_info.value.message == "Execution failed (runner contract violation)."


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_timeout_returns_timed_out(
    runner: DockerToolRunner,
    mock_docker_client: MagicMock,
    tool_version: ToolVersion,
) -> None:
    client_instance = mock_docker_client.return_value

    volume = MagicMock()
    volume.name = "work-volume"
    client_instance.volumes.create.return_value = volume

    container = MagicMock()
    client_instance.containers.create.return_value = container
    container.logs.side_effect = [b"stdout", b"stderr"]
    container.wait.side_effect = ReadTimeout("timeout")
    container.get_archive.side_effect = NotFound("Not found")

    result = await runner.execute(
        run_id=uuid4(),
        version=tool_version,
        context=RunContext.SANDBOX,
        input_files=[("input.txt", b"input")],
    )

    assert result.status is RunStatus.TIMED_OUT
    assert result.ui_result.error_summary == "Execution timed out."


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_artifact_extraction_violation_returns_failed(
    runner: DockerToolRunner,
    mock_docker_client: MagicMock,
    tool_version: ToolVersion,
    mock_artifacts: MagicMock,
) -> None:
    client_instance = mock_docker_client.return_value

    volume = MagicMock()
    volume.name = "work-volume"
    client_instance.volumes.create.return_value = volume

    container = MagicMock()
    client_instance.containers.create.return_value = container
    container.logs.side_effect = [b"stdout", b"stderr"]
    container.wait.return_value = {"StatusCode": 0}

    result_tar = create_result_tar(
        status="succeeded",
        outputs=[{"kind": "html_sandboxed", "html": "<p>Hi</p>"}],
        artifacts=[{"path": "output/report.txt", "bytes": 1}],
    )

    def get_archive_side_effect(*, path: str):
        if path == "/work/result.json":
            return [result_tar], {}
        if path == "/work/output":
            return [b"tar_stream"], {}
        raise NotFound("Not found")

    container.get_archive.side_effect = get_archive_side_effect
    mock_artifacts.store_output_archive.side_effect = DomainError(
        code=ErrorCode.INTERNAL_ERROR,
        message="Runner contract violation: unsafe artifact path",
    )

    with pytest.raises(DomainError) as exc_info:
        await runner.execute(
            run_id=uuid4(),
            version=tool_version,
            context=RunContext.SANDBOX,
            input_files=[("input.txt", b"input")],
        )

    assert exc_info.value.code is ErrorCode.INTERNAL_ERROR
    assert exc_info.value.message == "Execution failed (artifact extraction violation)."
