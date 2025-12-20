from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

from skriptoteket.domain.scripting.models import RunStatus
from skriptoteket.domain.scripting.ui.contract_v2 import UiPayloadV2


class StartActionCommand(BaseModel):
    """Start an interactive tool turn (ADR-0024)."""

    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    context: str
    action_id: str
    input: dict[str, JsonValue] = Field(default_factory=dict)
    expected_state_rev: int

    @field_validator("action_id")
    @classmethod
    def _validate_action_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("action_id is required")
        if len(normalized) > 64:
            raise ValueError("action_id must be 64 characters or less")
        return normalized


class StartActionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: UUID
    state_rev: int


class InteractiveSessionState(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    context: str
    state: dict[str, JsonValue]
    state_rev: int
    latest_run_id: UUID | None = None


class GetSessionStateQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    context: str


class GetSessionStateResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_state: InteractiveSessionState


class RunArtifact(BaseModel):
    model_config = ConfigDict(frozen=True)

    artifact_id: str
    path: str
    bytes: int
    download_url: str


class RunDetails(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: UUID
    status: RunStatus
    ui_payload: UiPayloadV2 | None = None
    artifacts: list[RunArtifact] = Field(default_factory=list)


class GetRunQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: UUID


class GetRunResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    run: RunDetails


class ListArtifactsQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: UUID


class ListArtifactsResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: UUID
    artifacts: list[RunArtifact]

