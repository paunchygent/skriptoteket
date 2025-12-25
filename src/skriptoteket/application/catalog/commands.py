from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.catalog.models import Tool


class CreateDraftToolCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    summary: str | None = None


class CreateDraftToolResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool: Tool


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


class UpdateToolMetadataCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    title: str
    summary: str | None = None


class UpdateToolMetadataResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool: Tool


class UpdateToolSlugCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    slug: str


class UpdateToolSlugResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool: Tool


class AssignMaintainerCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    user_id: UUID
    reason: str | None = None


class AssignMaintainerResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    user_id: UUID


class RemoveMaintainerCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    user_id: UUID
    reason: str | None = None


class RemoveMaintainerResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    user_id: UUID


class UpdateToolTaxonomyCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    profession_ids: list[UUID]
    category_ids: list[UUID]


class UpdateToolTaxonomyResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    profession_ids: list[UUID]
    category_ids: list[UUID]
