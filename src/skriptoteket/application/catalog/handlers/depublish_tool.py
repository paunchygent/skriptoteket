from __future__ import annotations

from skriptoteket.application.catalog.commands import DepublishToolCommand, DepublishToolResult
from skriptoteket.domain.catalog.models import set_tool_published_state
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.catalog import DepublishToolHandlerProtocol, ToolRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class DepublishToolHandler(DepublishToolHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._tools = tools
        self._clock = clock

    async def handle(self, *, actor: User, command: DepublishToolCommand) -> DepublishToolResult:
        require_at_least_role(user=actor, role=Role.ADMIN)

        now = self._clock.now()
        async with self._uow:
            tool = await self._tools.get_by_id(tool_id=command.tool_id)
            if tool is None:
                raise not_found("Tool", str(command.tool_id))

            updated_tool = set_tool_published_state(tool=tool, is_published=False, now=now)
            if updated_tool is tool:
                return DepublishToolResult(tool=tool)

            persisted = await self._tools.set_published(
                tool_id=tool.id,
                is_published=False,
                now=now,
            )
            return DepublishToolResult(tool=persisted)
