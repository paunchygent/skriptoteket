from __future__ import annotations

from collections.abc import Collection
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.errors import validation_error


class Suggestion(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    submitted_by_user_id: UUID

    title: str
    description: str

    profession_slugs: tuple[str, ...]
    category_slugs: tuple[str, ...]

    created_at: datetime
    updated_at: datetime


def create_suggestion(
    *,
    suggestion_id: UUID,
    submitted_by_user_id: UUID,
    title: str,
    description: str,
    profession_slugs: Collection[str],
    category_slugs: Collection[str],
    now: datetime,
) -> Suggestion:
    normalized_title = title.strip()
    if not normalized_title:
        raise validation_error("Title is required")
    if len(normalized_title) > 255:
        raise validation_error("Title must be 255 characters or less")

    normalized_description = description.strip()
    if not normalized_description:
        raise validation_error("Description is required")

    professions = tuple(slug.strip() for slug in profession_slugs)
    if not professions:
        raise validation_error("At least one profession is required")
    if len(set(professions)) != len(professions):
        raise validation_error("Duplicate professions are not allowed")
    if any(not slug for slug in professions):
        raise validation_error("Profession slugs must not be empty")

    categories = tuple(slug.strip() for slug in category_slugs)
    if not categories:
        raise validation_error("At least one category is required")
    if len(set(categories)) != len(categories):
        raise validation_error("Duplicate categories are not allowed")
    if any(not slug for slug in categories):
        raise validation_error("Category slugs must not be empty")

    return Suggestion(
        id=suggestion_id,
        submitted_by_user_id=submitted_by_user_id,
        title=normalized_title,
        description=normalized_description,
        profession_slugs=professions,
        category_slugs=categories,
        created_at=now,
        updated_at=now,
    )
