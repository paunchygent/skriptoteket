from __future__ import annotations

from typing import Protocol
from uuid import UUID

from skriptoteket.domain.catalog.models import Tool, is_placeholder_tool_slug, validate_tool_slug
from skriptoteket.domain.errors import validation_error


class ListToolTagIds(Protocol):
    async def __call__(self, *, tool_id: UUID) -> tuple[list[UUID], list[UUID]]: ...


async def ensure_tool_publish_requirements(
    *,
    tool: Tool,
    list_tag_ids: ListToolTagIds,
) -> None:
    if is_placeholder_tool_slug(slug=tool.slug):
        raise validation_error(
            "URL-namn måste ändras (får inte börja med 'draft-') innan publicering.",
            details={"tool_id": str(tool.id), "slug": tool.slug},
        )

    normalized_slug = validate_tool_slug(slug=tool.slug)
    if normalized_slug != tool.slug:
        raise validation_error(
            "Ogiltigt URL-namn. Använd bara a–z, 0–9 och bindestreck (1–128 tecken).",
            details={"tool_id": str(tool.id), "slug": tool.slug},
        )

    profession_ids, category_ids = await list_tag_ids(tool_id=tool.id)
    if not profession_ids or not category_ids:
        raise validation_error(
            "Välj minst ett yrke och minst en kategori innan publicering.",
            details={
                "tool_id": str(tool.id),
                "profession_count": len(profession_ids),
                "category_count": len(category_ids),
            },
        )
