from __future__ import annotations

from typing import Protocol
from uuid import UUID

from skriptoteket.application.catalog.queries import (
    ListAllCategoriesQuery,
    ListAllCategoriesResult,
    ListCategoriesForProfessionQuery,
    ListCategoriesForProfessionResult,
    ListProfessionsQuery,
    ListProfessionsResult,
    ListToolsByTagsQuery,
    ListToolsByTagsResult,
)
from skriptoteket.domain.catalog.models import Category, Profession, Tool


class ProfessionRepositoryProtocol(Protocol):
    async def list_all(self) -> list[Profession]: ...
    async def get_by_slug(self, slug: str) -> Profession | None: ...


class CategoryRepositoryProtocol(Protocol):
    async def list_all(self) -> list[Category]: ...
    async def list_for_profession(self, *, profession_id: UUID) -> list[Category]: ...
    async def get_by_slug(self, slug: str) -> Category | None: ...
    async def get_for_profession_by_slug(
        self, *, profession_id: UUID, category_slug: str
    ) -> Category | None: ...


class ToolRepositoryProtocol(Protocol):
    async def list_by_tags(self, *, profession_id: UUID, category_id: UUID) -> list[Tool]: ...

    async def get_by_id(self, *, tool_id: UUID) -> Tool | None: ...
    async def get_by_slug(self, *, slug: str) -> Tool | None: ...

    async def create_draft(
        self,
        *,
        tool: Tool,
        profession_ids: list[UUID],
        category_ids: list[UUID],
    ) -> Tool: ...


class ListProfessionsHandlerProtocol(Protocol):
    async def handle(self, query: ListProfessionsQuery) -> ListProfessionsResult: ...


class ListCategoriesForProfessionHandlerProtocol(Protocol):
    async def handle(
        self, query: ListCategoriesForProfessionQuery
    ) -> ListCategoriesForProfessionResult: ...


class ListToolsByTagsHandlerProtocol(Protocol):
    async def handle(self, query: ListToolsByTagsQuery) -> ListToolsByTagsResult: ...


class ListAllCategoriesHandlerProtocol(Protocol):
    async def handle(self, query: ListAllCategoriesQuery) -> ListAllCategoriesResult: ...
