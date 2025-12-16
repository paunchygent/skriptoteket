from __future__ import annotations

from skriptoteket.application.catalog.commands import (
    UpdateToolMetadataCommand,
    UpdateToolMetadataResult,
)
from skriptoteket.domain.catalog.models import update_tool_metadata
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.catalog import ToolRepositoryProtocol, UpdateToolMetadataHandlerProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class UpdateToolMetadataHandler(UpdateToolMetadataHandlerProtocol):
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

    async def handle(
        self,
        *,
        actor: User,
        command: UpdateToolMetadataCommand,
    ) -> UpdateToolMetadataResult:
        require_at_least_role(user=actor, role=Role.ADMIN)

        now = self._clock.now()
        async with self._uow:
            tool = await self._tools.get_by_id(tool_id=command.tool_id)
            if tool is None:
                raise not_found("Tool", str(command.tool_id))

            updated = update_tool_metadata(
                tool=tool,
                title=command.title,
                summary=command.summary,
                now=now,
            )
            if updated is tool:
                return UpdateToolMetadataResult(tool=tool)

            persisted = await self._tools.update_metadata(
                tool_id=tool.id,
                title=updated.title,
                summary=updated.summary,
                now=now,
            )

        return UpdateToolMetadataResult(tool=persisted)
