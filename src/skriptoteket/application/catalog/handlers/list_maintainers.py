from __future__ import annotations

from skriptoteket.application.catalog.queries import ListMaintainersQuery, ListMaintainersResult
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.catalog import (
    ListMaintainersHandlerProtocol,
    ToolMaintainerRepositoryProtocol,
    ToolRepositoryProtocol,
)
from skriptoteket.protocols.identity import UserRepositoryProtocol


class ListMaintainersHandler(ListMaintainersHandlerProtocol):
    def __init__(
        self,
        *,
        tools: ToolRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        users: UserRepositoryProtocol,
    ) -> None:
        self._tools = tools
        self._maintainers = maintainers
        self._users = users

    async def handle(self, *, actor: User, query: ListMaintainersQuery) -> ListMaintainersResult:
        require_at_least_role(user=actor, role=Role.ADMIN)

        tool = await self._tools.get_by_id(tool_id=query.tool_id)
        if tool is None:
            raise not_found("Tool", str(query.tool_id))

        maintainer_uuids = await self._maintainers.list_maintainers(tool_id=query.tool_id)

        maintainer_users = []
        for user_id in maintainer_uuids:
            user = await self._users.get_by_id(user_id=user_id)
            if user is not None:
                maintainer_users.append(user)

        return ListMaintainersResult(
            tool_id=query.tool_id,
            maintainers=maintainer_users,
        )
