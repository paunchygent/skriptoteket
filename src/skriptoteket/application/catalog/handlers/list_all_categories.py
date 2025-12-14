from __future__ import annotations

from skriptoteket.application.catalog.queries import ListAllCategoriesQuery, ListAllCategoriesResult
from skriptoteket.protocols.catalog import (
    CategoryRepositoryProtocol,
    ListAllCategoriesHandlerProtocol,
)


class ListAllCategoriesHandler(ListAllCategoriesHandlerProtocol):
    def __init__(self, *, categories: CategoryRepositoryProtocol) -> None:
        self._categories = categories

    async def handle(self, query: ListAllCategoriesQuery) -> ListAllCategoriesResult:
        del query  # no filters yet
        return ListAllCategoriesResult(categories=await self._categories.list_all())
