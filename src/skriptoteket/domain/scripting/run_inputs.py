from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.scripting.file_refs import parse_file_ref
from skriptoteket.domain.scripting.input_files import sanitize_input_filename


class ResolvedInputFile(BaseModel):
    """Input file staged for a runner execution (with optional FileRef)."""

    model_config = ConfigDict(frozen=True)

    name: str
    content: bytes
    ref: str | None = None

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        try:
            return sanitize_input_filename(input_filename=value)
        except DomainError as exc:
            raise ValueError(exc.message) from exc

    @field_validator("ref")
    @classmethod
    def _validate_ref(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            parse_file_ref(value=value)
        except DomainError as exc:
            raise ValueError(exc.message) from exc
        return value
