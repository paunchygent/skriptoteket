from __future__ import annotations

import io
import json
import tarfile
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from docker.errors import DockerException, NotFound
from pydantic import JsonValue
from requests.exceptions import ReadTimeout

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.models import RunContext, RunStatus, ToolVersion
from skriptoteket.domain.scripting.run_inputs import ResolvedInputFile
from skriptoteket.infrastructure.runner.docker_runner import DockerToolRunner


def create_result_tar(
    *,
    status: str,
    outputs: list[dict[str, object]],
    error_summary: str | None = None,
    next_actions: list[dict[str, object]] | None = None,
    state_update: dict[str, object] | None = None,
    error: dict[str, object] | None = None,
    artifacts: list[dict[str, object]] | None = None,
    promotions: dict[str, object] | None = None,
    contract_version: int = 3,
) -> bytes:
    payload = {
        "contract_version": contract_version,
        "status": status,
        "error_summary": error_summary,
        "error": error,
        "outputs": outputs,
        "next_actions": next_actions or [],
        "state_update": state_update or {"kind": "no_change"},
        "artifacts": artifacts or [],
        "promotions": promotions,
    }
    result_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        info = tarfile.TarInfo(name="result.json")
        info.size = len(result_bytes)
        tar.addfile(info, io.BytesIO(result_bytes))

    return tar_buffer.getvalue()


def read_tar_member(*, tar_bytes: bytes, name: str) -> bytes:
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:*") as tar:
        member = tar.getmember(name)
        extracted = tar.extractfile(member)
        if extracted is None:
            raise AssertionError(f"Missing tar member: {name}")
        with extracted:
            return extracted.read()


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
        input_files=[
            ResolvedInputFile(
                name="input.txt",
                content=b"input",
                ref="session:input.txt",
                field="documents",
            )
        ],
        input_values={},
        memory_json=b'{"settings":{}}',
        action_payload=None,
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
    assert env["SKRIPTOTEKET_INPUT_DIR"] == "/work/input"
    assert "SKRIPTOTEKET_INPUT_PATH" not in env
    assert env["SKRIPTOTEKET_MEMORY_PATH"] == "/work/memory.json"
    assert "SKRIPTOTEKET_INPUTS" not in env
    assert "SKRIPTOTEKET_ACTION" not in env
    assert "SKRIPTOTEKET_INPUT_MANIFEST" not in env

    archive_bytes = container.put_archive.call_args.kwargs["data"]
    request_payload = json.loads(read_tar_member(tar_bytes=archive_bytes, name="request.json"))
    assert request_payload == {
        "schema_version": 1,
        "inputs": {"values": {}},
        "files": [
            {
                "name": "input.txt",
                "path": "/work/input/input.txt",
                "bytes": 5,
                "ref": "session:input.txt",
                "field": "documents",
            }
        ],
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_includes_action_payload_in_request_json(
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

    result_tar = create_result_tar(
        status="succeeded",
        outputs=[{"kind": "notice", "level": "info", "message": "ok"}],
    )

    def get_archive_side_effect(*, path: str):
        if path == "/work/result.json":
            return [result_tar], {}
        if path == "/work/output":
            return [b"tar_stream"], {}
        raise NotFound("Not found")

    container.get_archive.side_effect = get_archive_side_effect

    action_payload: dict[str, JsonValue] = {
        "action_id": "confirm",
        "input": {"x": 1},
        "state": {"y": 2},
    }
    await runner.execute(
        run_id=uuid4(),
        version=tool_version,
        context=RunContext.SANDBOX,
        input_files=[
            ResolvedInputFile(
                name="input.txt",
                content=b"input",
                ref="session:input.txt",
                field="documents",
            )
        ],
        input_values={},
        memory_json=b'{"settings":{}}',
        action_payload=action_payload,
    )

    archive_bytes = container.put_archive.call_args.kwargs["data"]
    request_payload = json.loads(read_tar_member(tar_bytes=archive_bytes, name="request.json"))
    assert request_payload["action"] == action_payload


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
            input_files=[
                ResolvedInputFile(
                    name="input.txt",
                    content=b"input",
                    ref="session:input.txt",
                    field="documents",
                )
            ],
            input_values={},
            memory_json=b'{"settings":{}}',
            action_payload=None,
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
        input_files=[
            ResolvedInputFile(
                name="input.txt",
                content=b"input",
                ref="session:input.txt",
                field="documents",
            )
        ],
        input_values={},
        memory_json=b'{"settings":{}}',
        action_payload=None,
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
            input_files=[
                ResolvedInputFile(
                    name="input.txt",
                    content=b"input",
                    ref="session:input.txt",
                    field="documents",
                )
            ],
            input_values={},
            memory_json=b'{"settings":{}}',
            action_payload=None,
        )

    assert exc_info.value.code is ErrorCode.INTERNAL_ERROR
    assert exc_info.value.message == "Execution failed (artifact extraction violation)."


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_returns_service_unavailable_when_docker_sock_missing(
    runner: DockerToolRunner,
    tool_version: ToolVersion,
    mock_capacity: MagicMock,
    monkeypatch,
) -> None:
    import docker

    from skriptoteket.infrastructure.runner.docker import errors as docker_errors

    monkeypatch.setattr(
        docker,
        "from_env",
        MagicMock(side_effect=DockerException("Docker is unavailable")),
    )
    monkeypatch.setattr(
        docker_errors.os.path,
        "exists",
        lambda path: False if path == "/var/run/docker.sock" else True,
    )

    with pytest.raises(DomainError) as exc_info:
        await runner.execute(
            run_id=uuid4(),
            version=tool_version,
            context=RunContext.SANDBOX,
            input_files=[
                ResolvedInputFile(
                    name="input.txt",
                    content=b"input",
                    ref="session:input.txt",
                    field="documents",
                )
            ],
            input_values={},
            memory_json=b'{"settings":{}}',
            action_payload=None,
        )

    assert exc_info.value.code is ErrorCode.SERVICE_UNAVAILABLE
    assert "pdm run dev-stack start" in exc_info.value.message
    mock_capacity.release.assert_awaited_once()
