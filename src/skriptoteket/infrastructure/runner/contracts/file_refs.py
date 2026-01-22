from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.scripting.input_files import sanitize_input_filename

FILE_REF_SESSION_PREFIX = "session:"
FILE_REF_VAULT_PREFIX = "vault:"


def validate_session_ref_name(*, value: str) -> str:
    return sanitize_input_filename(input_filename=value)


def validate_vault_ref_id(*, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise validation_error("vault ref id is required")
    try:
        return str(UUID(normalized))
    except ValueError as exc:
        raise validation_error("vault ref id must be a UUID") from exc


def parse_file_ref(*, value: str) -> tuple[str, str]:
    normalized = value.strip()
    if not normalized:
        raise validation_error("file ref is required")

    if normalized.startswith(FILE_REF_SESSION_PREFIX):
        name = normalized.removeprefix(FILE_REF_SESSION_PREFIX)
        return "session", validate_session_ref_name(value=name)

    if normalized.startswith(FILE_REF_VAULT_PREFIX):
        file_id = normalized.removeprefix(FILE_REF_VAULT_PREFIX)
        return "vault", validate_vault_ref_id(value=file_id)

    raise validation_error("file ref must start with session: or vault:")
