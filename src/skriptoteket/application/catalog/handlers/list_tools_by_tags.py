from __future__ import annotations

from skriptoteket.application.catalog.queries import ListToolsByTagsQuery, ListToolsByTagsResult
from skriptoteket.domain.errors import not_found
from skriptoteket.protocols.catalog import (
    CategoryRepositoryProtocol,
    ListToolsByTagsHandlerProtocol,
    ProfessionRepositoryProtocol,
    ToolRepositoryProtocol,
)


class ListToolsByTagsHandler(ListToolsByTagsHandlerProtocol):
    def __init__(
        self,
        *,
        professions: ProfessionRepositoryProtocol,
        categories: CategoryRepositoryProtocol,
        tools: ToolRepositoryProtocol,
    ) -> None:
        self._professions = professions
        self._categories = categories
        self._tools = tools

    async def handle(self, query: ListToolsByTagsQuery) -> ListToolsByTagsResult:
        profession = await self._professions.get_by_slug(query.profession_slug)
        if profession is None:
            raise not_found("profession", query.profession_slug)

        category = await self._categories.get_for_profession_by_slug(
            profession_id=profession.id, category_slug=query.category_slug
        )
        if category is None:
            raise not_found("category", query.category_slug)

        tools = await self._tools.list_by_tags(
            profession_id=profession.id,
            category_id=category.id,
        )
        return ListToolsByTagsResult(profession=profession, category=category, tools=tools)

