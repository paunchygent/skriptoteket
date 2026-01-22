from __future__ import annotations

import io
import json
import tarfile
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from docker.errors import NotFound
from requests.exceptions import ReadTimeout

from skriptoteket.domain.scripting.models import RunContext, RunStatus, ToolVersion
from skriptoteket.infrastructure.runner.docker_runner import DockerToolRunner


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


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("container_status", ["missing", "created"])
async def test_try_adopt_returns_none_when_no_adoptable_container(
    runner: DockerToolRunner,
    mock_docker_client: MagicMock,
    tool_version: ToolVersion,
    container_status: str,
) -> None:
    run_id = uuid4()
    client_instance = mock_docker_client.return_value
    client_instance.volumes.list.return_value = []

    created_container: MagicMock | None = None
    if container_status == "missing":
        client_instance.containers.list.return_value = []
    elif container_status == "created":
        created_container = MagicMock()
        created_container.status = "created"
        client_instance.containers.list.return_value = [created_container]
    else:  # pragma: no cover
        raise AssertionError(f"Unexpected container_status: {container_status}")

    adopted = await runner.try_adopt(
        run_id=run_id,
        version=tool_version,
        context=RunContext.SANDBOX,
    )

    assert adopted is None
    if created_container is not None:
        assert created_container.remove.call_count >= 1


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case", "expected_status"),
    [
        ("success", RunStatus.SUCCEEDED),
        ("timeout", RunStatus.TIMED_OUT),
    ],
)
async def test_try_adopt_finalizes_container_and_archives_output(
    runner: DockerToolRunner,
    mock_docker_client: MagicMock,
    tool_version: ToolVersion,
    mock_artifacts: MagicMock,
    case: str,
    expected_status: RunStatus,
) -> None:
    run_id = uuid4()
    client_instance = mock_docker_client.return_value
    client_instance.volumes.list.return_value = []

    container = MagicMock()
    container.status = "exited" if case == "success" else "running"
    container.logs.side_effect = [b"stdout", b"stderr"]
    if case == "success":
        container.wait.return_value = {"StatusCode": 0}
        result_tar = create_result_tar(
            status="succeeded",
            outputs=[{"kind": "html_sandboxed", "html": "<p>Hi</p>"}],
            artifacts=[{"path": "output/report.txt", "bytes": 1}],
        )
    else:
        container.wait.side_effect = [ReadTimeout(), {"StatusCode": 137}]
        result_tar = b""

    def get_archive_side_effect(*, path: str):
        if case == "success" and path == "/work/result.json":
            return [result_tar], {}
        if path == "/work/output":
            return [b"tar_stream"], {}
        raise NotFound("Not found")

    container.get_archive.side_effect = get_archive_side_effect
    client_instance.containers.list.return_value = [container]

    adopted = await runner.try_adopt(
        run_id=run_id,
        version=tool_version,
        context=RunContext.SANDBOX,
    )

    assert adopted is not None
    assert adopted.status is expected_status
    mock_artifacts.store_output_archive.assert_called_once()
