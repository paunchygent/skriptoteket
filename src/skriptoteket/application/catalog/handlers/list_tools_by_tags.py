from __future__ import annotations

from skriptoteket.application.catalog.queries import ListToolsByTagsQuery, ListToolsByTagsResult
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.identity.role_guards import has_at_least_role
from skriptoteket.protocols.catalog import (
    CategoryRepositoryProtocol,
    ListToolsByTagsHandlerProtocol,
    ProfessionRepositoryProtocol,
    ToolRepositoryProtocol,
)
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol


class ListToolsByTagsHandler(ListToolsByTagsHandlerProtocol):
    def __init__(
        self,
        *,
        professions: ProfessionRepositoryProtocol,
        categories: CategoryRepositoryProtocol,
        tools: ToolRepositoryProtocol,
        curated_apps: CuratedAppRegistryProtocol,
    ) -> None:
        self._professions = professions
        self._categories = categories
        self._tools = tools
        self._curated_apps = curated_apps

    async def handle(self, *, actor: User, query: ListToolsByTagsQuery) -> ListToolsByTagsResult:
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

        curated_apps = [
            app
            for app in self._curated_apps.list_all()
            if app.matches_placement(
                profession_slug=profession.slug,
                category_slug=category.slug,
            )
            and has_at_least_role(user=actor, role=app.min_role)
        ]
        curated_apps.sort(key=lambda app: app.title.casefold())

        return ListToolsByTagsResult(
            profession=profession,
            category=category,
            tools=tools,
            curated_apps=curated_apps,
        )
