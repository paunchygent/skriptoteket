import json

import pytest

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.runner.result_contract import parse_runner_result_json


def test_parse_runner_result_json_success() -> None:
    payload = {
        "contract_version": 1,
        "status": "succeeded",
        "html_output": "<p>ok</p>",
        "error_summary": None,
        "artifacts": [{"path": "output/report.pdf", "bytes": 12}],
    }
    result = parse_runner_result_json(result_json_bytes=json.dumps(payload).encode("utf-8"))
    assert result.contract_version == 1
    assert result.status == "succeeded"
    assert result.artifacts[0].path == "output/report.pdf"


def test_parse_runner_result_json_rejects_unknown_contract_version() -> None:
    payload = {
        "contract_version": 2,
        "status": "succeeded",
        "html_output": "",
        "error_summary": None,
        "artifacts": [],
    }
    with pytest.raises(DomainError) as exc_info:
        parse_runner_result_json(result_json_bytes=json.dumps(payload).encode("utf-8"))
    assert exc_info.value.code == ErrorCode.INTERNAL_ERROR


def test_parse_runner_result_json_rejects_invalid_artifact_path() -> None:
    payload = {
        "contract_version": 1,
        "status": "succeeded",
        "html_output": "",
        "error_summary": None,
        "artifacts": [{"path": "../evil.txt", "bytes": 1}],
    }
    with pytest.raises(DomainError) as exc_info:
        parse_runner_result_json(result_json_bytes=json.dumps(payload).encode("utf-8"))
    assert exc_info.value.code == ErrorCode.INTERNAL_ERROR
