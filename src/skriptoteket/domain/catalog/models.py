from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.errors import validation_error


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


class ToolVersionStats(BaseModel):
    """Version statistics for admin tool list enrichment (ADR-0033)."""

    model_config = ConfigDict(frozen=True)

    version_count: int
    latest_version_state: str | None  # "draft", "in_review", or None
    has_pending_review: bool


def set_tool_published_state(*, tool: Tool, is_published: bool, now: datetime) -> Tool:
    if tool.is_published == is_published:
        return tool
    return tool.model_copy(update={"is_published": is_published, "updated_at": now})


def _validate_tool_title(*, title: str) -> str:
    normalized_title = title.strip()
    if not normalized_title:
        raise validation_error("Title is required")
    if len(normalized_title) > 255:
        raise validation_error("Title must be 255 characters or less")
    return normalized_title


def _normalize_optional_summary(summary: str | None) -> str | None:
    if summary is None:
        return None
    normalized_summary = summary.strip()
    return normalized_summary if normalized_summary else None


def update_tool_metadata(*, tool: Tool, title: str, summary: str | None, now: datetime) -> Tool:
    normalized_title = _validate_tool_title(title=title)
    normalized_summary = _normalize_optional_summary(summary)

    if tool.title == normalized_title and tool.summary == normalized_summary:
        return tool

    return tool.model_copy(
        update={
            "title": normalized_title,
            "summary": normalized_summary,
            "updated_at": now,
        }
    )
