from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from skriptoteket.domain.scripting.models import RunContext, ToolRun, ToolVersion
from skriptoteket.domain.scripting.tool_inputs import ToolInputSchema
from skriptoteket.domain.scripting.tool_settings import ToolSettingsSchema

type InputFile = tuple[str, bytes]


class SessionFilesMode(StrEnum):
    NONE = "none"
    REUSE = "reuse"
    CLEAR = "clear"


class SchemaName(StrEnum):
    SETTINGS_SCHEMA = "settings_schema"
    INPUT_SCHEMA = "input_schema"


class SchemaValidationIssue(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_name: SchemaName = Field(alias="schema")
    path: str | None = None
    message: str
    details: dict[str, JsonValue] | None = None


class ToolVersionOverride(BaseModel):
    model_config = ConfigDict(frozen=True)

    entrypoint: str | None = None
    source_code: str | None = None
    settings_schema: ToolSettingsSchema | None = None
    input_schema: ToolInputSchema | None = None
    usage_instructions: str | None = None


class SandboxSnapshotPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    entrypoint: str = Field(..., min_length=1, max_length=128)
    source_code: str = Field(..., min_length=1)
    settings_schema: ToolSettingsSchema | None = None
    input_schema: ToolInputSchema = Field(default_factory=list)
    usage_instructions: str | None = None


class ExecuteToolVersionCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    version_id: UUID
    snapshot_id: UUID | None = None
    context: RunContext
    settings_context: str | None = None
    version_override: ToolVersionOverride | None = None
    input_files: list[InputFile] = Field(default_factory=list)
    input_values: dict[str, JsonValue] = Field(default_factory=dict)
    action_payload: dict[str, JsonValue] | None = None


class ExecuteToolVersionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    run: ToolRun
    normalized_state: dict[str, JsonValue] = Field(default_factory=dict)


class CreateDraftVersionCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    derived_from_version_id: UUID | None = None
    entrypoint: str = "run_tool"
    source_code: str
    settings_schema: ToolSettingsSchema | None = None
    input_schema: ToolInputSchema = Field(default_factory=list)
    usage_instructions: str | None = None
    change_summary: str | None = None


class CreateDraftVersionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: ToolVersion


class SaveDraftVersionCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    version_id: UUID
    entrypoint: str = "run_tool"
    source_code: str
    settings_schema: ToolSettingsSchema | None = None
    input_schema: ToolInputSchema = Field(default_factory=list)
    usage_instructions: str | None = None
    change_summary: str | None = None
    expected_parent_version_id: UUID


class SaveDraftVersionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: ToolVersion


class SubmitForReviewCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    version_id: UUID
    review_note: str | None = None


class SubmitForReviewResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: ToolVersion


class PublishVersionCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    version_id: UUID
    change_summary: str | None = None


class PublishVersionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    new_active_version: ToolVersion
    archived_reviewed_version: ToolVersion
    archived_previous_active_version: ToolVersion | None = None


class RequestChangesCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    version_id: UUID
    message: str | None = None


class RequestChangesResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    new_draft_version: ToolVersion
    archived_in_review_version: ToolVersion


class RunSandboxCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    version_id: UUID
    snapshot_payload: SandboxSnapshotPayload
    input_files: list[InputFile] = Field(default_factory=list)
    input_values: dict[str, JsonValue] = Field(default_factory=dict)
    session_context: str | None = None
    session_files_mode: SessionFilesMode = SessionFilesMode.NONE


class RunSandboxResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    run: ToolRun
    state_rev: int | None = None  # Populated when run has next_actions
    snapshot_id: UUID


class RunActiveToolCommand(BaseModel):
    """Command for user-facing execution of published tools."""

    model_config = ConfigDict(frozen=True)

    tool_slug: str
    input_files: list[InputFile] = Field(default_factory=list)
    input_values: dict[str, JsonValue] = Field(default_factory=dict)
    session_context: str = "default"
    session_files_mode: SessionFilesMode = SessionFilesMode.NONE


class RunActiveToolResult(BaseModel):
    """Result from user-facing tool execution."""

    model_config = ConfigDict(frozen=True)

    run: ToolRun


class RollbackVersionCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    version_id: UUID  # The archived version to rollback to


class RollbackVersionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    new_active_version: ToolVersion
    archived_previous_active_version: ToolVersion | None = None


class ValidateToolSchemasCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    settings_schema: JsonValue | None = None
    input_schema: JsonValue | None = None


class ValidateToolSchemasResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    valid: bool
    issues: list[SchemaValidationIssue] = Field(default_factory=list)
