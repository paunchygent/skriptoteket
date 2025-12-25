from __future__ import annotations

from skriptoteket.application.catalog.commands import CreateDraftToolCommand, CreateDraftToolResult
from skriptoteket.domain.catalog.models import create_draft_tool
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.catalog import (
    CreateDraftToolHandlerProtocol,
    ToolMaintainerRepositoryProtocol,
    ToolRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class CreateDraftToolHandler(CreateDraftToolHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._tools = tools
        self._maintainers = maintainers
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self, *, actor: User, command: CreateDraftToolCommand
    ) -> CreateDraftToolResult:
        require_at_least_role(user=actor, role=Role.ADMIN)

        now = self._clock.now()
        tool_id = self._id_generator.new_uuid()
        tool = create_draft_tool(
            tool_id=tool_id,
            owner_user_id=actor.id,
            title=command.title,
            summary=command.summary,
            now=now,
        )

        async with self._uow:
            persisted = await self._tools.create_draft(
                tool=tool, profession_ids=[], category_ids=[]
            )
            await self._maintainers.add_maintainer(tool_id=tool.id, user_id=actor.id)

        return CreateDraftToolResult(tool=persisted)
