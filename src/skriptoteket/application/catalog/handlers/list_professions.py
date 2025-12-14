from __future__ import annotations

from skriptoteket.application.catalog.queries import ListProfessionsQuery, ListProfessionsResult
from skriptoteket.protocols.catalog import (
    ListProfessionsHandlerProtocol,
    ProfessionRepositoryProtocol,
)


class ListProfessionsHandler(ListProfessionsHandlerProtocol):
    def __init__(self, *, professions: ProfessionRepositoryProtocol) -> None:
        self._professions = professions

    async def handle(self, query: ListProfessionsQuery) -> ListProfessionsResult:
        del query  # no filters yet
        return ListProfessionsResult(professions=await self._professions.list_all())
