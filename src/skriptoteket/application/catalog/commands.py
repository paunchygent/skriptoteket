from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.catalog.models import Tool


class PublishToolCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID


class PublishToolResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool: Tool


class DepublishToolCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID


class DepublishToolResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool: Tool
