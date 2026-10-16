"""Pure filename rules for stem-only vault renames."""

from __future__ import annotations

from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.scripting.input_files import sanitize_input_filename


def rename_vault_filename(*, stem: str, extension: str) -> str:
    """Keep exactly one record-owned extension, never infer it from teacher text."""
    normalized = stem.strip()
    while extension and normalized.casefold().endswith(extension.casefold()):
        normalized = normalized[: -len(extension)].strip()
    if not normalized:
        raise validation_error("Filnamnet måste innehålla ett namn före filändelsen.")
    return sanitize_input_filename(input_filename=f"{normalized}{extension}")
