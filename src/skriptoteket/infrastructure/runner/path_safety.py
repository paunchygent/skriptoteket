from __future__ import annotations

from pathlib import PurePosixPath

from skriptoteket.domain.errors import DomainError, ErrorCode


def normalize_posix_relative_path(*, path: str) -> PurePosixPath:
    """Normalize a runner-supplied relative path (POSIX separators) with strict traversal rules."""
    normalized = path.strip()
    if not normalized:
        raise DomainError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Runner contract violation: empty path",
        )

    posix_path = PurePosixPath(normalized)
    if posix_path.is_absolute():
        raise DomainError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Runner contract violation: absolute paths are not allowed",
            details={"path": path},
        )

    normalized_parts: list[str] = []
    for part in posix_path.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            raise DomainError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Runner contract violation: path traversal is not allowed",
                details={"path": path},
            )
        normalized_parts.append(part)

    if not normalized_parts:
        raise DomainError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Runner contract violation: invalid path",
            details={"path": path},
        )

    return PurePosixPath(*normalized_parts)


def validate_output_path(*, path: str) -> PurePosixPath:
    """Validate a runner artifact path is under output/ (ADR-0015)."""
    normalized = normalize_posix_relative_path(path=path)
    if normalized.parts[0] != "output":
        raise DomainError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Runner contract violation: artifact paths must be under output/",
            details={"path": path},
        )
    return normalized
