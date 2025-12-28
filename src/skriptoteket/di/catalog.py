"""Catalog domain provider: tool browsing and maintainer management handlers."""

from __future__ import annotations

from dishka import Provider, Scope, provide

from skriptoteket.application.catalog.filtering import CatalogFilterService
from skriptoteket.application.catalog.handlers.assign_maintainer import AssignMaintainerHandler
from skriptoteket.application.catalog.handlers.create_draft_tool import CreateDraftToolHandler
from skriptoteket.application.catalog.handlers.depublish_tool import DepublishToolHandler
from skriptoteket.application.catalog.handlers.list_all_categories import ListAllCategoriesHandler
from skriptoteket.application.catalog.handlers.list_all_tools import ListAllToolsHandler
from skriptoteket.application.catalog.handlers.list_categories_for_profession import (
    ListCategoriesForProfessionHandler,
)
from skriptoteket.application.catalog.handlers.list_maintainers import ListMaintainersHandler
from skriptoteket.application.catalog.handlers.list_professions import ListProfessionsHandler
from skriptoteket.application.catalog.handlers.list_recent_tools import ListRecentToolsHandler
from skriptoteket.application.catalog.handlers.list_tool_taxonomy import (
    ListToolTaxonomyHandler,
)
from skriptoteket.application.catalog.handlers.list_tools_by_tags import ListToolsByTagsHandler
from skriptoteket.application.catalog.handlers.list_tools_for_admin import ListToolsForAdminHandler
from skriptoteket.application.catalog.handlers.list_tools_for_contributor import (
    ListToolsForContributorHandler,
)
from skriptoteket.application.catalog.handlers.publish_tool import PublishToolHandler
from skriptoteket.application.catalog.handlers.remove_maintainer import RemoveMaintainerHandler
from skriptoteket.application.catalog.handlers.update_tool_metadata import UpdateToolMetadataHandler
from skriptoteket.application.catalog.handlers.update_tool_slug import UpdateToolSlugHandler
from skriptoteket.application.catalog.handlers.update_tool_taxonomy import (
    UpdateToolTaxonomyHandler,
)
from skriptoteket.protocols.catalog import (
    AssignMaintainerHandlerProtocol,
    CatalogFilterProtocol,
    CategoryRepositoryProtocol,
    CreateDraftToolHandlerProtocol,
    DepublishToolHandlerProtocol,
    ListAllCategoriesHandlerProtocol,
    ListAllToolsHandlerProtocol,
    ListCategoriesForProfessionHandlerProtocol,
    ListMaintainersHandlerProtocol,
    ListProfessionsHandlerProtocol,
    ListRecentToolsHandlerProtocol,
    ListToolsByTagsHandlerProtocol,
    ListToolsForAdminHandlerProtocol,
    ListToolsForContributorHandlerProtocol,
    ListToolTaxonomyHandlerProtocol,
    ProfessionRepositoryProtocol,
    PublishToolHandlerProtocol,
    RemoveMaintainerHandlerProtocol,
    ToolMaintainerAuditRepositoryProtocol,
    ToolMaintainerRepositoryProtocol,
    ToolRepositoryProtocol,
    UpdateToolMetadataHandlerProtocol,
    UpdateToolSlugHandlerProtocol,
    UpdateToolTaxonomyHandlerProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.favorites import FavoritesRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import UserRepositoryProtocol
from skriptoteket.protocols.scripting import (
    ToolRunRepositoryProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class CatalogProvider(Provider):
    """Provides catalog/tool browsing handlers."""

    @provide(scope=Scope.REQUEST)
    def list_professions_handler(
        self, professions: ProfessionRepositoryProtocol
    ) -> ListProfessionsHandlerProtocol:
        return ListProfessionsHandler(professions=professions)

    @provide(scope=Scope.REQUEST)
    def list_categories_for_profession_handler(
        self,
        professions: ProfessionRepositoryProtocol,
        categories: CategoryRepositoryProtocol,
    ) -> ListCategoriesForProfessionHandlerProtocol:
        return ListCategoriesForProfessionHandler(professions=professions, categories=categories)

    @provide(scope=Scope.REQUEST)
    def list_all_categories_handler(
        self, categories: CategoryRepositoryProtocol
    ) -> ListAllCategoriesHandlerProtocol:
        return ListAllCategoriesHandler(categories=categories)

    @provide(scope=Scope.REQUEST)
    def list_tools_by_tags_handler(
        self,
        professions: ProfessionRepositoryProtocol,
        categories: CategoryRepositoryProtocol,
        tools: ToolRepositoryProtocol,
        curated_apps: CuratedAppRegistryProtocol,
    ) -> ListToolsByTagsHandlerProtocol:
        return ListToolsByTagsHandler(
            professions=professions,
            categories=categories,
            tools=tools,
            curated_apps=curated_apps,
        )

    @provide(scope=Scope.APP)
    def catalog_filter(self) -> CatalogFilterProtocol:
        return CatalogFilterService()

    @provide(scope=Scope.REQUEST)
    def list_all_tools_handler(
        self,
        professions: ProfessionRepositoryProtocol,
        categories: CategoryRepositoryProtocol,
        tools: ToolRepositoryProtocol,
        curated_apps: CuratedAppRegistryProtocol,
        favorites: FavoritesRepositoryProtocol,
        catalog_filter: CatalogFilterProtocol,
    ) -> ListAllToolsHandlerProtocol:
        return ListAllToolsHandler(
            professions=professions,
            categories=categories,
            tools=tools,
            curated_apps=curated_apps,
            favorites=favorites,
            catalog_filter=catalog_filter,
        )

    @provide(scope=Scope.REQUEST)
    def list_recent_tools_handler(
        self,
        runs: ToolRunRepositoryProtocol,
        tools: ToolRepositoryProtocol,
        curated_apps: CuratedAppRegistryProtocol,
        favorites: FavoritesRepositoryProtocol,
    ) -> ListRecentToolsHandlerProtocol:
        return ListRecentToolsHandler(
            runs=runs,
            tools=tools,
            curated_apps=curated_apps,
            favorites=favorites,
        )

    @provide(scope=Scope.REQUEST)
    def list_tools_for_admin_handler(
        self,
        tools: ToolRepositoryProtocol,
        versions: ToolVersionRepositoryProtocol,
    ) -> ListToolsForAdminHandlerProtocol:
        return ListToolsForAdminHandler(tools=tools, versions=versions)

    @provide(scope=Scope.REQUEST)
    def create_draft_tool_handler(
        self,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> CreateDraftToolHandlerProtocol:
        return CreateDraftToolHandler(
            uow=uow,
            tools=tools,
            maintainers=maintainers,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def publish_tool_handler(
        self,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        versions: ToolVersionRepositoryProtocol,
        clock: ClockProtocol,
    ) -> PublishToolHandlerProtocol:
        return PublishToolHandler(uow=uow, tools=tools, versions=versions, clock=clock)

    @provide(scope=Scope.REQUEST)
    def depublish_tool_handler(
        self,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        clock: ClockProtocol,
    ) -> DepublishToolHandlerProtocol:
        return DepublishToolHandler(uow=uow, tools=tools, clock=clock)

    @provide(scope=Scope.REQUEST)
    def update_tool_metadata_handler(
        self,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        clock: ClockProtocol,
    ) -> UpdateToolMetadataHandlerProtocol:
        return UpdateToolMetadataHandler(uow=uow, tools=tools, clock=clock)

    @provide(scope=Scope.REQUEST)
    def update_tool_slug_handler(
        self,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        clock: ClockProtocol,
    ) -> UpdateToolSlugHandlerProtocol:
        return UpdateToolSlugHandler(uow=uow, tools=tools, clock=clock)

    @provide(scope=Scope.REQUEST)
    def update_tool_taxonomy_handler(
        self,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        professions: ProfessionRepositoryProtocol,
        categories: CategoryRepositoryProtocol,
        clock: ClockProtocol,
    ) -> UpdateToolTaxonomyHandlerProtocol:
        return UpdateToolTaxonomyHandler(
            uow=uow,
            tools=tools,
            professions=professions,
            categories=categories,
            clock=clock,
        )

    # Maintainer management handlers

    @provide(scope=Scope.REQUEST)
    def list_maintainers_handler(
        self,
        tools: ToolRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        users: UserRepositoryProtocol,
    ) -> ListMaintainersHandlerProtocol:
        return ListMaintainersHandler(tools=tools, maintainers=maintainers, users=users)

    @provide(scope=Scope.REQUEST)
    def assign_maintainer_handler(
        self,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        users: UserRepositoryProtocol,
        audit: ToolMaintainerAuditRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> AssignMaintainerHandlerProtocol:
        return AssignMaintainerHandler(
            uow=uow,
            tools=tools,
            maintainers=maintainers,
            users=users,
            audit=audit,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def remove_maintainer_handler(
        self,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        users: UserRepositoryProtocol,
        audit: ToolMaintainerAuditRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> RemoveMaintainerHandlerProtocol:
        return RemoveMaintainerHandler(
            uow=uow,
            tools=tools,
            maintainers=maintainers,
            users=users,
            audit=audit,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def list_tools_for_contributor_handler(
        self,
        tools: ToolRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
    ) -> ListToolsForContributorHandlerProtocol:
        return ListToolsForContributorHandler(tools=tools, maintainers=maintainers)

    @provide(scope=Scope.REQUEST)
    def list_tool_taxonomy_handler(
        self,
        tools: ToolRepositoryProtocol,
    ) -> ListToolTaxonomyHandlerProtocol:
        return ListToolTaxonomyHandler(tools=tools)
