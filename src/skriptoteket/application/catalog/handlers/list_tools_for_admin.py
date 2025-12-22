from __future__ import annotations

from skriptoteket.application.catalog.queries import ListToolsForAdminQuery, ListToolsForAdminResult
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.catalog import ListToolsForAdminHandlerProtocol, ToolRepositoryProtocol
from skriptoteket.protocols.scripting import ToolVersionRepositoryProtocol


class ListToolsForAdminHandler(ListToolsForAdminHandlerProtocol):
    """Handler for listing tools with version statistics (ADR-0033)."""

    def __init__(
        self,
        *,
        tools: ToolRepositoryProtocol,
        versions: ToolVersionRepositoryProtocol,
    ) -> None:
        self._tools = tools
        self._versions = versions

    async def handle(
        self, *, actor: User, query: ListToolsForAdminQuery
    ) -> ListToolsForAdminResult:
        del query  # no filters yet
        require_at_least_role(user=actor, role=Role.ADMIN)

        all_tools = await self._tools.list_all()
        tool_ids = [t.id for t in all_tools]
        version_stats = await self._versions.get_version_stats_for_tools(tool_ids=tool_ids)

        return ListToolsForAdminResult(tools=all_tools, version_stats=version_stats)
