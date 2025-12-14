from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Profession(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    slug: str
    label: str
    sort_order: int
    created_at: datetime
    updated_at: datetime


class Category(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    slug: str
    label: str
    created_at: datetime
    updated_at: datetime


class Tool(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    slug: str
    title: str
    summary: str | None = None
    is_published: bool = False
    active_version_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


def set_tool_published_state(*, tool: Tool, is_published: bool, now: datetime) -> Tool:
    if tool.is_published == is_published:
        return tool
    return tool.model_copy(update={"is_published": is_published, "updated_at": now})
