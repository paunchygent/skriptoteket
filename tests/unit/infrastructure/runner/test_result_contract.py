import json

import pytest

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.runner.result_contract import parse_runner_result_json


def test_parse_runner_result_json_success() -> None:
    payload = {
        "contract_version": 2,
        "status": "succeeded",
        "error_summary": None,
        "outputs": [{"kind": "html_sandboxed", "html": "<p>ok</p>"}],
        "next_actions": [],
        "state": None,
        "artifacts": [{"path": "output/report.pdf", "bytes": 12}],
    }
    result = parse_runner_result_json(result_json_bytes=json.dumps(payload).encode("utf-8"))
    assert result.contract_version == 2
    assert result.status == "succeeded"
    assert result.artifacts[0].path == "output/report.pdf"


def test_parse_runner_result_json_rejects_unknown_contract_version() -> None:
    payload = {
        "contract_version": 1,
        "status": "succeeded",
        "error_summary": None,
        "outputs": [],
        "next_actions": [],
        "state": None,
        "artifacts": [],
    }
    with pytest.raises(DomainError) as exc_info:
        parse_runner_result_json(result_json_bytes=json.dumps(payload).encode("utf-8"))
    assert exc_info.value.code == ErrorCode.INTERNAL_ERROR


def test_parse_runner_result_json_rejects_invalid_artifact_path() -> None:
    payload = {
        "contract_version": 2,
        "status": "succeeded",
        "error_summary": None,
        "outputs": [],
        "next_actions": [],
        "state": None,
        "artifacts": [{"path": "../evil.txt", "bytes": 1}],
    }
    with pytest.raises(DomainError) as exc_info:
        parse_runner_result_json(result_json_bytes=json.dumps(payload).encode("utf-8"))
    assert exc_info.value.code == ErrorCode.INTERNAL_ERROR


def test_parse_runner_result_json_with_invalid_json_raises_domain_error() -> None:
    with pytest.raises(DomainError) as exc_info:
        parse_runner_result_json(result_json_bytes=b"not valid json {")

    assert exc_info.value.code == ErrorCode.INTERNAL_ERROR


def test_parse_runner_result_json_with_invalid_utf8_raises_domain_error() -> None:
    with pytest.raises(DomainError) as exc_info:
        parse_runner_result_json(result_json_bytes=b"\xff\xfe invalid")

    assert exc_info.value.code == ErrorCode.INTERNAL_ERROR


def test_parse_runner_result_json_with_missing_required_fields_raises_domain_error() -> None:
    payload = {
        "contract_version": 2,
        # missing status
    }
    with pytest.raises(DomainError) as exc_info:
        parse_runner_result_json(result_json_bytes=json.dumps(payload).encode("utf-8"))

    assert exc_info.value.code == ErrorCode.INTERNAL_ERROR


def test_parse_runner_result_json_with_invalid_status_raises_domain_error() -> None:
    payload = {
        "contract_version": 2,
        "status": "unknown_status",
        "error_summary": None,
        "outputs": [],
        "next_actions": [],
        "state": None,
        "artifacts": [],
    }
    with pytest.raises(DomainError) as exc_info:
        parse_runner_result_json(result_json_bytes=json.dumps(payload).encode("utf-8"))

    assert exc_info.value.code == ErrorCode.INTERNAL_ERROR


def test_parse_runner_result_json_with_null_error_summary_succeeds() -> None:
    payload = {
        "contract_version": 2,
        "status": "succeeded",
        "error_summary": None,
        "outputs": [{"kind": "html_sandboxed", "html": "<p>ok</p>"}],
        "next_actions": [],
        "state": None,
        "artifacts": [],
    }

    result = parse_runner_result_json(result_json_bytes=json.dumps(payload).encode("utf-8"))

    assert result.error_summary is None
    assert result.status == "succeeded"


def test_parse_runner_result_json_with_error_summary_succeeds() -> None:
    payload = {
        "contract_version": 2,
        "status": "failed",
        "error_summary": "Something went wrong",
        "outputs": [],
        "next_actions": [],
        "state": None,
        "artifacts": [],
    }

    result = parse_runner_result_json(result_json_bytes=json.dumps(payload).encode("utf-8"))

    assert result.error_summary == "Something went wrong"
    assert result.status == "failed"
