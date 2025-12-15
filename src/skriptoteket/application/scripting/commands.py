from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.scripting.models import RunContext, ToolRun


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
