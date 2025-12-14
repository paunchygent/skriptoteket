from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from skriptoteket.application.catalog.handlers.list_categories_for_profession import (
    ListCategoriesForProfessionHandler,
)
from skriptoteket.application.catalog.queries import ListCategoriesForProfessionQuery
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.catalog import CategoryRepositoryProtocol, ProfessionRepositoryProtocol
from tests.fixtures.catalog_fixtures import make_category, make_profession


@pytest.mark.asyncio
async def test_list_categories_for_profession_returns_ordered_categories(now: datetime) -> None:
    profession = make_profession(now=now)
    categories = [
        make_category(slug="mentorskap", label="Mentorskap", now=now),
        make_category(slug="administration", label="Administration", now=now),
    ]

    professions = AsyncMock(spec=ProfessionRepositoryProtocol)
    professions.get_by_slug.return_value = profession

    category_repo = AsyncMock(spec=CategoryRepositoryProtocol)
    category_repo.list_for_profession.return_value = categories

    handler = ListCategoriesForProfessionHandler(professions=professions, categories=category_repo)
    result = await handler.handle(ListCategoriesForProfessionQuery(profession_slug=profession.slug))

    assert result.profession == profession
    assert result.categories == categories
    category_repo.list_for_profession.assert_awaited_once_with(profession_id=profession.id)


@pytest.mark.asyncio
async def test_list_categories_for_profession_raises_when_profession_missing() -> None:
    professions = AsyncMock(spec=ProfessionRepositoryProtocol)
    professions.get_by_slug.return_value = None

    category_repo = AsyncMock(spec=CategoryRepositoryProtocol)

    handler = ListCategoriesForProfessionHandler(professions=professions, categories=category_repo)

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(ListCategoriesForProfessionQuery(profession_slug="nope"))

    assert exc_info.value.code == ErrorCode.NOT_FOUND
    category_repo.list_for_profession.assert_not_awaited()

