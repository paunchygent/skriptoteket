from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, JsonValue

from skriptoteket.domain.scripting.ui.contract_v2 import UiActionField


class ToolSettingsState(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    schema_version: str | None
    settings_schema: list[UiActionField] | None
    values: dict[str, JsonValue]
    state_rev: int


class GetToolSettingsQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID


class GetToolSettingsResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    settings: ToolSettingsState


class GetToolVersionSettingsQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    version_id: UUID


class GetToolVersionSettingsResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    settings: ToolSettingsState


class UpdateToolSettingsCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    expected_state_rev: int
    values: dict[str, JsonValue]


class UpdateToolSettingsResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    settings: ToolSettingsState


class UpdateToolVersionSettingsCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    version_id: UUID
    expected_state_rev: int
    values: dict[str, JsonValue]


class UpdateToolVersionSettingsResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    settings: ToolSettingsState
