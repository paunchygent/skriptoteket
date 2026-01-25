from __future__ import annotations

import json

import pytest

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.web.api.v1.tools import _parse_file_fields, _parse_file_refs_by_field


@pytest.mark.unit
def test_parse_file_fields_requires_payload_when_files_present() -> None:
    with pytest.raises(DomainError) as exc_info:
        _parse_file_fields(None, expected_len=1)

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert exc_info.value.message == "file_fields is required when uploading files"


@pytest.mark.unit
def test_parse_file_fields_rejects_length_mismatch() -> None:
    raw = json.dumps(["documents"])

    with pytest.raises(DomainError) as exc_info:
        _parse_file_fields(raw, expected_len=2)

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert exc_info.value.details["file_fields"] == 1
    assert exc_info.value.details["files"] == 2


@pytest.mark.unit
def test_parse_file_fields_trims_entries() -> None:
    raw = json.dumps([" documents ", "images"])

    parsed = _parse_file_fields(raw, expected_len=2)

    assert parsed == ["documents", "images"]


@pytest.mark.unit
def test_parse_file_refs_by_field_rejects_invalid_json() -> None:
    with pytest.raises(DomainError) as exc_info:
        _parse_file_refs_by_field("{not-json")

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert exc_info.value.message == "file_refs_by_field must be valid JSON"


@pytest.mark.unit
def test_parse_file_refs_by_field_rejects_non_object() -> None:
    raw = json.dumps(["session:doc.txt"])

    with pytest.raises(DomainError) as exc_info:
        _parse_file_refs_by_field(raw)

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert exc_info.value.message == "file_refs_by_field must be a JSON object"


@pytest.mark.unit
def test_parse_file_refs_by_field_rejects_non_string_values() -> None:
    raw = json.dumps({"documents": [1]})

    with pytest.raises(DomainError) as exc_info:
        _parse_file_refs_by_field(raw)

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert exc_info.value.message == "file_refs_by_field values must be lists of strings"


@pytest.mark.unit
def test_parse_file_refs_by_field_trims_values() -> None:
    raw = json.dumps({"documents": [" session:doc.txt ", " "]})

    parsed = _parse_file_refs_by_field(raw)

    assert parsed == {"documents": ["session:doc.txt"]}
