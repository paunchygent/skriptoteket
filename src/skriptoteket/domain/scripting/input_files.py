from __future__ import annotations

from pathlib import PurePosixPath

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.domain.errors import ErrorDetails, validation_error


class InputFileEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    bytes: int


class InputManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    files: list[InputFileEntry] = Field(default_factory=list)


def sanitize_input_filename(*, input_filename: str) -> str:
    """Sanitize a user-supplied input filename to a safe “file name only” form."""
    normalized = input_filename.strip()
    if not normalized:
        raise validation_error("input_filename is required")

    posix = PurePosixPath(normalized)
    if posix.is_absolute() or ".." in posix.parts or "/" in normalized or "\\" in normalized:
        raise validation_error("input_filename must be a file name")

    if len(normalized) > 255:
        raise validation_error("input_filename must be 255 characters or less")

    return normalized


def normalize_input_files(
    *, input_files: list[tuple[str, bytes]]
) -> tuple[list[tuple[str, bytes]], InputManifest]:
    if not input_files:
        raise validation_error("input_files is required")

    normalized_files: list[tuple[str, bytes]] = []
    manifest_entries: list[InputFileEntry] = []

    seen: set[str] = set()
    collisions: dict[str, list[str]] = {}

    for original_name, content in input_files:
        safe_name = sanitize_input_filename(input_filename=original_name)
        if safe_name in seen:
            collisions.setdefault(safe_name, []).append(original_name)
            continue

        seen.add(safe_name)
        normalized_files.append((safe_name, content))
        manifest_entries.append(InputFileEntry(name=safe_name, bytes=len(content)))

    if collisions:
        details: ErrorDetails = {
            "collisions": {
                safe_name: [safe_name, *originals] for safe_name, originals in collisions.items()
            }
        }
        raise validation_error(
            "Duplicate input filenames after sanitization; rename files locally.",
            details=details,
        )

    return normalized_files, InputManifest(files=manifest_entries)

