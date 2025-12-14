from __future__ import annotations

from skriptoteket.application.catalog.queries import ListToolsForAdminQuery, ListToolsForAdminResult
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.catalog import ListToolsForAdminHandlerProtocol, ToolRepositoryProtocol


class ListToolsForAdminHandler(ListToolsForAdminHandlerProtocol):
    def __init__(self, *, tools: ToolRepositoryProtocol) -> None:
        self._tools = tools

    async def handle(
        self, *, actor: User, query: ListToolsForAdminQuery
    ) -> ListToolsForAdminResult:
        del query  # no filters yet
        require_at_least_role(user=actor, role=Role.ADMIN)
        return ListToolsForAdminResult(tools=await self._tools.list_all())
