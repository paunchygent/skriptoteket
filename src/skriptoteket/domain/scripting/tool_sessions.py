from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, JsonValue, field_validator

from skriptoteket.domain.errors import validation_error


class ToolSession(BaseModel):
    """Persisted per-user per-tool session state (ADR-0024)."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    tool_id: UUID
    user_id: UUID
    context: str

    state: dict[str, JsonValue]
    state_rev: int

    created_at: datetime
    updated_at: datetime

    @field_validator("context")
    @classmethod
    def _validate_context(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("context is required")
        if len(normalized) > 64:
            raise ValueError("context must be 64 characters or less")
        return normalized

    @field_validator("state_rev")
    @classmethod
    def _validate_state_rev(cls, value: int) -> int:
        if value < 0:
            raise ValueError("state_rev must be >= 0")
        return value


def normalize_tool_session_context(*, context: str) -> str:
    normalized = context.strip()
    if not normalized:
        raise validation_error("context is required")
    if len(normalized) > 64:
        raise validation_error("context must be 64 characters or less")
    return normalized


def validate_expected_state_rev(*, expected_state_rev: int) -> None:
    if expected_state_rev < 0:
        raise validation_error(
            "expected_state_rev must be >= 0",
            details={"expected_state_rev": expected_state_rev},
        )
