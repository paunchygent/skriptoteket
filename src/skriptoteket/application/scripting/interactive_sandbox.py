"""Interactive sandbox action commands and results (ADR-0038)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, JsonValue


class StartSandboxActionCommand(BaseModel):
    """Command for starting a sandbox action."""

    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    version_id: UUID
    action_id: str
    input: dict[str, JsonValue]
    expected_state_rev: int


class StartSandboxActionResult(BaseModel):
    """Result from starting a sandbox action."""

    model_config = ConfigDict(frozen=True)

    run_id: UUID
    state_rev: int
