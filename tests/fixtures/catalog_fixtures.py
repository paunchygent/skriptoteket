from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from skriptoteket.domain.catalog.models import Category, Profession, Tool


def make_profession(
    *,
    slug: str = "larare",
    label: str = "Lärare",
    sort_order: int = 10,
    now: datetime,
    profession_id: UUID | None = None,
) -> Profession:
    return Profession(
        id=profession_id or uuid4(),
        slug=slug,
        label=label,
        sort_order=sort_order,
        created_at=now,
        updated_at=now,
    )


def make_category(
    *,
    slug: str = "lektionsplanering",
    label: str = "Lektionsplanering",
    now: datetime,
    category_id: UUID | None = None,
) -> Category:
    return Category(
        id=category_id or uuid4(),
        slug=slug,
        label=label,
        created_at=now,
        updated_at=now,
    )


def make_tool(
    *,
    slug: str = "demo-tool",
    title: str = "Demo tool",
    summary: str | None = None,
    now: datetime,
    tool_id: UUID | None = None,
) -> Tool:
    return Tool(
        id=tool_id or uuid4(),
        slug=slug,
        title=title,
        summary=summary,
        created_at=now,
        updated_at=now,
    )

