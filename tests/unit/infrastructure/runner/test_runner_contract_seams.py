import io
import json
import tarfile
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.domain.scripting.models import RunContext, RunStatus, ToolVersion
from skriptoteket.domain.scripting.run_inputs import ResolvedInputFile
from skriptoteket.infrastructure.runner.docker.contract_selection import (
    StaticRunnerContractSelector,
)
from skriptoteket.infrastructure.runner.docker.request_factory import V3RunnerRequestFactory
from skriptoteket.infrastructure.runner.docker.result_parser import V3RunnerResultParser
from skriptoteket.protocols.runner import ArtifactManagerProtocol


def read_tar_member(*, tar_bytes: bytes, name: str) -> bytes:
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:*") as tar:
        member = tar.getmember(name)
        extracted = tar.extractfile(member)
        if extracted is None:
            raise AssertionError(f"Missing tar member: {name}")
        with extracted:
            return extracted.read()


@pytest.mark.unit
def test_v3_request_factory_builds_request(
    tool_version: ToolVersion,
    runner_request_factory: V3RunnerRequestFactory,
) -> None:
    memory_json = b'{"settings":{"mode":"test"}}'
    request = runner_request_factory.build_request(
        version=tool_version,
        input_files=[
            ResolvedInputFile(
                name="input.txt",
                content=b"input",
                ref="session:input.txt",
                field="documents",
            )
        ],
        input_values={"alpha": 1, "documents": ["session:doc.txt"]},
        memory_json=memory_json,
        action_payload=None,
    )

    assert "SKRIPTOTEKET_INPUTS" not in request.env
    assert "SKRIPTOTEKET_INPUT_MANIFEST" not in request.env
    assert "SKRIPTOTEKET_ACTION" not in request.env
    request_payload = json.loads(request.request_json_bytes.decode("utf-8"))
    assert request_payload == {
        "schema_version": 1,
        "inputs": {"values": {"alpha": 1, "documents": ["session:doc.txt"]}},
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

    names = []
    with tarfile.open(fileobj=io.BytesIO(request.workdir_archive), mode="r:*") as tar:
        names = [member.name for member in tar.getmembers()]

    assert "script.py" in names
    assert "memory.json" in names
    assert "request.json" in names
    assert "input/input.txt" in names
    assert read_tar_member(tar_bytes=request.workdir_archive, name="memory.json") == memory_json
    assert read_tar_member(tar_bytes=request.workdir_archive, name="input/input.txt") == b"input"


@pytest.mark.unit
def test_v3_result_parser_wraps_payload(
    runner_result_parser: V3RunnerResultParser,
) -> None:
    container = MagicMock()
    artifacts = MagicMock(spec=ArtifactManagerProtocol)
    artifacts.store_output_archive.return_value = ArtifactsManifest(artifacts=[])

    def get_archive_side_effect(*, path: str):
        if path == "/work/output":
            return [b"tar_stream"], {}
        raise AssertionError(f"Unexpected get_archive path: {path}")

    container.get_archive.side_effect = get_archive_side_effect

    payload = {
        "contract_version": 3,
        "status": "succeeded",
        "error_summary": None,
        "error": None,
        "outputs": [{"kind": "notice", "level": "info", "message": "ok"}],
        "next_actions": [],
        "state_update": {"kind": "set", "state": {"x": 1}},
        "artifacts": [],
        "promotions": {"requests": [], "results": []},
    }
    parsed = runner_result_parser.parse(
        container=container,
        result_json_bytes=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        run_id=UUID(int=0),
        stdout="stdout",
        stderr="stderr",
        artifacts=artifacts,
        output_max_error_summary_bytes=2048,
    )

    assert parsed.status is RunStatus.SUCCEEDED
    assert parsed.ui_result.outputs[0].kind == "notice"
    assert parsed.ui_result.state == {"x": 1}
    assert parsed.promotions is not None
    artifacts.store_output_archive.assert_called_once()


@pytest.mark.unit
def test_static_contract_selector_returns_contract(
    tool_version: ToolVersion,
    runner_contract,
) -> None:
    selector = StaticRunnerContractSelector(contract=runner_contract)
    selected = selector.select(version=tool_version, context=RunContext.SANDBOX)
    assert selected is runner_contract
