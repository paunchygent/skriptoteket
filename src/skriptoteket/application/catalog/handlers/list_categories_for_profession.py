from __future__ import annotations

from skriptoteket.application.catalog.queries import (
    ListCategoriesForProfessionQuery,
    ListCategoriesForProfessionResult,
)
from skriptoteket.domain.errors import not_found
from skriptoteket.protocols.catalog import (
    CategoryRepositoryProtocol,
    ListCategoriesForProfessionHandlerProtocol,
    ProfessionRepositoryProtocol,
)


class ListCategoriesForProfessionHandler(ListCategoriesForProfessionHandlerProtocol):
    def __init__(
        self,
        *,
        professions: ProfessionRepositoryProtocol,
        categories: CategoryRepositoryProtocol,
    ) -> None:
        self._professions = professions
        self._categories = categories

    async def handle(
        self, query: ListCategoriesForProfessionQuery
    ) -> ListCategoriesForProfessionResult:
        profession = await self._professions.get_by_slug(query.profession_slug)
        if profession is None:
            raise not_found("profession", query.profession_slug)

        categories = await self._categories.list_for_profession(profession_id=profession.id)
        return ListCategoriesForProfessionResult(profession=profession, categories=categories)
