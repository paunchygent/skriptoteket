from __future__ import annotations

from skriptoteket.application.scripting.commands import (
    RollbackVersionCommand,
    RollbackVersionResult,
)
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_any_role
from skriptoteket.domain.scripting.models import rollback_to_version
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.scripting import (
    RollbackVersionHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class RollbackVersionHandler(RollbackVersionHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        versions: ToolVersionRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._tools = tools
        self._versions = versions
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        command: RollbackVersionCommand,
    ) -> RollbackVersionResult:
        require_any_role(user=actor, roles={Role.SUPERUSER})

        now = self._clock.now()
        new_active_version_id = self._id_generator.new_uuid()

        async with self._uow:
            archived_version = await self._versions.get_by_id(version_id=command.version_id)
            if archived_version is None:
                raise not_found("ToolVersion", str(command.version_id))

            tool = await self._tools.get_by_id(tool_id=archived_version.tool_id)
            if tool is None:
                raise not_found("Tool", str(archived_version.tool_id))

            previous_active_version = await self._versions.get_active_for_tool(
                tool_id=archived_version.tool_id
            )
            new_active_version_number = await self._versions.get_next_version_number(
                tool_id=archived_version.tool_id
            )

            result = rollback_to_version(
                archived_version=archived_version,
                new_active_version_id=new_active_version_id,
                new_active_version_number=new_active_version_number,
                published_by_user_id=actor.id,
                now=now,
                previous_active_version=previous_active_version,
            )

            archived_previous_active = None
            if result.archived_previous_active_version is not None:
                archived_previous_active = await self._versions.update(
                    version=result.archived_previous_active_version
                )

            new_active = await self._versions.create(version=result.new_active_version)
            await self._tools.set_active_version_id(
                tool_id=tool.id,
                active_version_id=new_active.id,
                now=now,
            )

        return RollbackVersionResult(
            new_active_version=new_active,
            archived_previous_active_version=archived_previous_active,
        )
