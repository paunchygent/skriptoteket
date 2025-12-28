from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from skriptoteket.application.catalog.commands import (
    AssignMaintainerCommand,
    AssignMaintainerResult,
    CreateDraftToolCommand,
    CreateDraftToolResult,
    DepublishToolCommand,
    DepublishToolResult,
    PublishToolCommand,
    PublishToolResult,
    RemoveMaintainerCommand,
    RemoveMaintainerResult,
    UpdateToolMetadataCommand,
    UpdateToolMetadataResult,
    UpdateToolSlugCommand,
    UpdateToolSlugResult,
    UpdateToolTaxonomyCommand,
    UpdateToolTaxonomyResult,
)
from skriptoteket.application.catalog.queries import (
    ListAllCategoriesQuery,
    ListAllCategoriesResult,
    ListAllToolsQuery,
    ListAllToolsResult,
    ListCategoriesForProfessionQuery,
    ListCategoriesForProfessionResult,
    ListMaintainersQuery,
    ListMaintainersResult,
    ListProfessionsQuery,
    ListProfessionsResult,
    ListRecentToolsQuery,
    ListRecentToolsResult,
    ListToolsByTagsQuery,
    ListToolsByTagsResult,
    ListToolsForAdminQuery,
    ListToolsForAdminResult,
    ListToolsForContributorQuery,
    ListToolsForContributorResult,
    ListToolTaxonomyQuery,
    ListToolTaxonomyResult,
)
from skriptoteket.domain.catalog.models import Category, Profession, Tool
from skriptoteket.domain.curated_apps.models import CuratedAppDefinition
from skriptoteket.domain.identity.models import User


class ProfessionRepositoryProtocol(Protocol):
    async def list_all(self) -> list[Profession]: ...
    async def get_by_slug(self, slug: str) -> Profession | None: ...
    async def list_by_ids(self, *, profession_ids: list[UUID]) -> list[Profession]: ...


class CategoryRepositoryProtocol(Protocol):
    async def list_all(self) -> list[Category]: ...
    async def list_for_profession(self, *, profession_id: UUID) -> list[Category]: ...
    async def get_by_slug(self, slug: str) -> Category | None: ...
    async def get_for_profession_by_slug(
        self, *, profession_id: UUID, category_slug: str
    ) -> Category | None: ...
    async def list_by_ids(self, *, category_ids: list[UUID]) -> list[Category]: ...


class ToolRepositoryProtocol(Protocol):
    async def list_by_tags(self, *, profession_id: UUID, category_id: UUID) -> list[Tool]: ...

    async def list_all(self) -> list[Tool]: ...

    async def list_by_ids(self, *, tool_ids: list[UUID]) -> list[Tool]: ...

    async def list_published_filtered(
        self,
        *,
        profession_ids: list[UUID] | None = None,
        category_ids: list[UUID] | None = None,
        search_term: str | None = None,
    ) -> list[Tool]: ...

    async def get_by_id(self, *, tool_id: UUID) -> Tool | None: ...
    async def get_by_slug(self, *, slug: str) -> Tool | None: ...

    async def set_published(
        self,
        *,
        tool_id: UUID,
        is_published: bool,
        now: datetime,
    ) -> Tool: ...

    async def set_active_version_id(
        self,
        *,
        tool_id: UUID,
        active_version_id: UUID | None,
        now: datetime,
    ) -> Tool: ...

    async def update_metadata(
        self,
        *,
        tool_id: UUID,
        title: str,
        summary: str | None,
        now: datetime,
    ) -> Tool: ...

    async def update_slug(
        self,
        *,
        tool_id: UUID,
        slug: str,
        now: datetime,
    ) -> Tool: ...

    async def create_draft(
        self,
        *,
        tool: Tool,
        profession_ids: list[UUID],
        category_ids: list[UUID],
    ) -> Tool: ...

    async def list_tag_ids(
        self,
        *,
        tool_id: UUID,
    ) -> tuple[list[UUID], list[UUID]]: ...

    async def replace_tags(
        self,
        *,
        tool_id: UUID,
        profession_ids: list[UUID],
        category_ids: list[UUID],
        now: datetime,
    ) -> None: ...


class ToolMaintainerRepositoryProtocol(Protocol):
    async def is_maintainer(self, *, tool_id: UUID, user_id: UUID) -> bool: ...

    async def add_maintainer(self, *, tool_id: UUID, user_id: UUID) -> None: ...

    async def list_maintainers(self, *, tool_id: UUID) -> list[UUID]: ...

    async def remove_maintainer(self, *, tool_id: UUID, user_id: UUID) -> None: ...

    async def list_tools_for_user(self, *, user_id: UUID) -> list[UUID]: ...


class ToolMaintainerAuditRepositoryProtocol(Protocol):
    async def log_action(
        self,
        *,
        log_id: UUID,
        tool_id: UUID,
        user_id: UUID,
        action: str,
        performed_by_user_id: UUID,
        performed_at: datetime,
        reason: str | None,
    ) -> None: ...


class CatalogFilterProtocol(Protocol):
    def filter_curated_apps(
        self,
        *,
        apps: list[CuratedAppDefinition],
        actor: User,
        profession_slugs: list[str] | None,
        category_slugs: list[str] | None,
        search_term: str | None,
    ) -> list[CuratedAppDefinition]: ...


class ListProfessionsHandlerProtocol(Protocol):
    async def handle(self, query: ListProfessionsQuery) -> ListProfessionsResult: ...


class ListCategoriesForProfessionHandlerProtocol(Protocol):
    async def handle(
        self, query: ListCategoriesForProfessionQuery
    ) -> ListCategoriesForProfessionResult: ...


class ListToolsByTagsHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        query: ListToolsByTagsQuery,
    ) -> ListToolsByTagsResult: ...


class ListAllToolsHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        query: ListAllToolsQuery,
    ) -> ListAllToolsResult: ...


class ListRecentToolsHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        query: ListRecentToolsQuery,
    ) -> ListRecentToolsResult: ...


class ListAllCategoriesHandlerProtocol(Protocol):
    async def handle(self, query: ListAllCategoriesQuery) -> ListAllCategoriesResult: ...


class ListToolsForAdminHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        query: ListToolsForAdminQuery,
    ) -> ListToolsForAdminResult: ...


class CreateDraftToolHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: CreateDraftToolCommand,
    ) -> CreateDraftToolResult: ...


class PublishToolHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: PublishToolCommand,
    ) -> PublishToolResult: ...


class DepublishToolHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: DepublishToolCommand,
    ) -> DepublishToolResult: ...


class UpdateToolMetadataHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: UpdateToolMetadataCommand,
    ) -> UpdateToolMetadataResult: ...


class UpdateToolSlugHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: UpdateToolSlugCommand,
    ) -> UpdateToolSlugResult: ...


class UpdateToolTaxonomyHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: UpdateToolTaxonomyCommand,
    ) -> UpdateToolTaxonomyResult: ...


class ListMaintainersHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        query: ListMaintainersQuery,
    ) -> ListMaintainersResult: ...


class AssignMaintainerHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: AssignMaintainerCommand,
    ) -> AssignMaintainerResult: ...


class RemoveMaintainerHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: RemoveMaintainerCommand,
    ) -> RemoveMaintainerResult: ...


class ListToolsForContributorHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        query: ListToolsForContributorQuery,
    ) -> ListToolsForContributorResult: ...


class ListToolTaxonomyHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        query: ListToolTaxonomyQuery,
    ) -> ListToolTaxonomyResult: ...
