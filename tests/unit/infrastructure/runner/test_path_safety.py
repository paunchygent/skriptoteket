from pathlib import PurePosixPath

import pytest

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.runner.path_safety import (
    normalize_posix_relative_path,
    validate_output_path,
)


def test_normalize_posix_relative_path_normalizes_dots() -> None:
    assert normalize_posix_relative_path(path="./output/./report.pdf") == PurePosixPath(
        "output", "report.pdf"
    )


def test_normalize_posix_relative_path_rejects_absolute_paths() -> None:
    with pytest.raises(DomainError) as exc_info:
        normalize_posix_relative_path(path="/output/report.pdf")
    assert exc_info.value.code == ErrorCode.INTERNAL_ERROR


def test_normalize_posix_relative_path_rejects_traversal() -> None:
    with pytest.raises(DomainError) as exc_info:
        normalize_posix_relative_path(path="output/../evil.txt")
    assert exc_info.value.code == ErrorCode.INTERNAL_ERROR


def test_validate_output_path_rejects_non_output_root() -> None:
    with pytest.raises(DomainError) as exc_info:
        validate_output_path(path="tmp/report.pdf")
    assert exc_info.value.code == ErrorCode.INTERNAL_ERROR


def test_validate_output_path_accepts_output_root() -> None:
    assert validate_output_path(path="output") == PurePosixPath("output")
