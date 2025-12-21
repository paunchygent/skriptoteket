import io
import tarfile
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.input_files import sanitize_input_filename
from skriptoteket.domain.scripting.models import ToolVersion, VersionState
from skriptoteket.infrastructure.runner.docker_runner import (
    _build_workdir_archive,
    _extract_first_file_from_tar_bytes,
    _truncate_utf8_bytes,
    _truncate_utf8_str,
)

# --- sanitize_input_filename tests ---


def test_sanitize_input_filename_with_valid_name_returns_name() -> None:
    result = sanitize_input_filename(input_filename="report.csv")

    assert result == "report.csv"


def test_sanitize_input_filename_with_path_separator_raises_validation_error() -> None:
    with pytest.raises(DomainError) as exc_info:
        sanitize_input_filename(input_filename="dir/file.csv")

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR


def test_sanitize_input_filename_with_backslash_raises_validation_error() -> None:
    with pytest.raises(DomainError) as exc_info:
        sanitize_input_filename(input_filename="dir\\file.csv")

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR


def test_sanitize_input_filename_with_parent_dir_traversal_raises_validation_error() -> None:
    with pytest.raises(DomainError) as exc_info:
        sanitize_input_filename(input_filename="..")

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR


def test_sanitize_input_filename_with_empty_raises_validation_error() -> None:
    with pytest.raises(DomainError) as exc_info:
        sanitize_input_filename(input_filename="")

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR


def test_sanitize_input_filename_with_whitespace_only_raises_validation_error() -> None:
    with pytest.raises(DomainError) as exc_info:
        sanitize_input_filename(input_filename="   ")

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR


def test_sanitize_input_filename_exceeding_255_chars_raises_validation_error() -> None:
    long_name = "a" * 256

    with pytest.raises(DomainError) as exc_info:
        sanitize_input_filename(input_filename=long_name)

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR


def test_sanitize_input_filename_at_255_chars_returns_name() -> None:
    name_255 = "a" * 255

    result = sanitize_input_filename(input_filename=name_255)

    assert result == name_255


# --- _truncate_utf8_bytes tests ---


def test_truncate_utf8_bytes_under_limit_returns_decoded_string() -> None:
    data = "hello".encode("utf-8")

    result = _truncate_utf8_bytes(data=data, max_bytes=100)

    assert result == "hello"


def test_truncate_utf8_bytes_at_limit_returns_decoded_string() -> None:
    data = "hello".encode("utf-8")

    result = _truncate_utf8_bytes(data=data, max_bytes=5)

    assert result == "hello"


def test_truncate_utf8_bytes_over_limit_truncates() -> None:
    data = "hello world".encode("utf-8")

    result = _truncate_utf8_bytes(data=data, max_bytes=5)

    assert result == "hello"


def test_truncate_utf8_bytes_with_multibyte_uses_replacement() -> None:
    # "åäö" is 6 bytes in UTF-8 (2 bytes each)
    data = "åäö".encode("utf-8")

    result = _truncate_utf8_bytes(data=data, max_bytes=3)

    # Truncated at byte 3, may produce replacement char for partial sequence
    assert len(result.encode("utf-8")) <= 3 or "�" in result


def test_truncate_utf8_bytes_with_zero_limit_returns_empty() -> None:
    data = "hello".encode("utf-8")

    result = _truncate_utf8_bytes(data=data, max_bytes=0)

    assert result == ""


# --- _truncate_utf8_str tests ---


def test_truncate_utf8_str_under_limit_returns_original() -> None:
    result = _truncate_utf8_str(value="hello", max_bytes=100)

    assert result == "hello"


def test_truncate_utf8_str_at_limit_returns_original() -> None:
    result = _truncate_utf8_str(value="hello", max_bytes=5)

    assert result == "hello"


def test_truncate_utf8_str_over_limit_truncates() -> None:
    result = _truncate_utf8_str(value="hello world", max_bytes=5)

    assert result == "hello"


def test_truncate_utf8_str_with_multibyte_truncates_safely() -> None:
    # "åäö" is 6 bytes in UTF-8
    result = _truncate_utf8_str(value="åäö", max_bytes=4)

    # Should truncate to 4 bytes max, preserving valid UTF-8
    assert len(result.encode("utf-8")) <= 4


def test_truncate_utf8_str_with_zero_limit_returns_empty() -> None:
    result = _truncate_utf8_str(value="hello", max_bytes=0)

    assert result == ""


# --- _build_workdir_archive tests ---


def _make_tool_version(source_code: str = "print('test')") -> ToolVersion:
    return ToolVersion(
        id=uuid4(),
        tool_id=uuid4(),
        version_number=1,
        state=VersionState.DRAFT,
        entrypoint="run_tool",
        source_code=source_code,
        content_hash="abc123",
        derived_from_version_id=None,
        created_by_user_id=uuid4(),
        created_at=datetime.now(timezone.utc),
    )


def test_build_workdir_archive_contains_script_and_input() -> None:
    version = _make_tool_version(source_code="def run_tool(): pass")

    archive_bytes = _build_workdir_archive(
        version=version,
        input_files=[("data.csv", b"col1,col2\n1,2")],
    )

    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r") as tar:
        names = tar.getnames()
        assert "script.py" in names
        assert "input" in names
        assert "input/data.csv" in names


def test_build_workdir_archive_script_has_correct_content() -> None:
    source = "def run_tool(): return '<p>ok</p>'"
    version = _make_tool_version(source_code=source)

    archive_bytes = _build_workdir_archive(
        version=version,
        input_files=[("file.txt", b"content")],
    )

    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r") as tar:
        script_member = tar.getmember("script.py")
        script_file = tar.extractfile(script_member)
        assert script_file is not None
        assert script_file.read().decode("utf-8") == source


def test_build_workdir_archive_input_has_correct_content() -> None:
    version = _make_tool_version()
    input_data = b"test input data"

    archive_bytes = _build_workdir_archive(
        version=version,
        input_files=[("input.txt", input_data)],
    )

    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r") as tar:
        input_file = tar.extractfile("input/input.txt")
        assert input_file is not None
        assert input_file.read() == input_data


# --- _extract_first_file_from_tar_bytes tests ---


def test_extract_first_file_from_tar_bytes_returns_file_content() -> None:
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        data = b"file content"
        info = tarfile.TarInfo(name="file.txt")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))

    result = _extract_first_file_from_tar_bytes(tar_bytes=tar_buffer.getvalue())

    assert result == b"file content"


def test_extract_first_file_from_tar_bytes_skips_directories() -> None:
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        dir_info = tarfile.TarInfo(name="dir")
        dir_info.type = tarfile.DIRTYPE
        tar.addfile(dir_info)

        data = b"actual file"
        file_info = tarfile.TarInfo(name="dir/file.txt")
        file_info.size = len(data)
        tar.addfile(file_info, io.BytesIO(data))

    result = _extract_first_file_from_tar_bytes(tar_bytes=tar_buffer.getvalue())

    assert result == b"actual file"


def test_extract_first_file_from_tar_bytes_empty_tar_raises_runtime_error() -> None:
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w"):
        pass

    with pytest.raises(RuntimeError, match="No file found"):
        _extract_first_file_from_tar_bytes(tar_bytes=tar_buffer.getvalue())
