from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from skriptoteket.domain.scripting.models import RunContext, ToolRun, ToolVersion

type InputFile = tuple[str, bytes]


class ExecuteToolVersionCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    version_id: UUID
    context: RunContext
    input_files: list[InputFile]


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
    change_summary: str | None = None


class CreateDraftVersionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: ToolVersion


class SaveDraftVersionCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    version_id: UUID
    entrypoint: str = "run_tool"
    source_code: str
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
    input_files: list[InputFile]


class RunSandboxResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    run: ToolRun


class RunActiveToolCommand(BaseModel):
    """Command for user-facing execution of published tools."""

    model_config = ConfigDict(frozen=True)

    tool_slug: str
    input_files: list[InputFile]


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
