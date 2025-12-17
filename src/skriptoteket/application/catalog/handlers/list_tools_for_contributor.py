from __future__ import annotations

from skriptoteket.application.catalog.queries import (
    ListToolsForContributorQuery,
    ListToolsForContributorResult,
)
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.catalog import (
    ListToolsForContributorHandlerProtocol,
    ToolMaintainerRepositoryProtocol,
    ToolRepositoryProtocol,
)


class ListToolsForContributorHandler(ListToolsForContributorHandlerProtocol):
    def __init__(
        self,
        *,
        tools: ToolRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
    ) -> None:
        self._tools = tools
        self._maintainers = maintainers

    async def handle(
        self,
        *,
        actor: User,
        query: ListToolsForContributorQuery,
    ) -> ListToolsForContributorResult:
        del query  # Uses actor.id, not query fields
        require_at_least_role(user=actor, role=Role.CONTRIBUTOR)

        tool_ids = await self._maintainers.list_tools_for_user(user_id=actor.id)

        tools = []
        for tool_id in tool_ids:
            tool = await self._tools.get_by_id(tool_id=tool_id)
            if tool is not None:
                tools.append(tool)

        return ListToolsForContributorResult(tools=tools)
