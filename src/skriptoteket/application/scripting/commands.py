from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.scripting.models import RunContext, ToolRun, ToolVersion


class ExecuteToolVersionCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    version_id: UUID
    context: RunContext
    input_filename: str
    input_bytes: bytes


class ExecuteToolVersionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    run: ToolRun


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


class RunSandboxCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    version_id: UUID
    input_filename: str
    input_bytes: bytes


class RunSandboxResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    run: ToolRun
