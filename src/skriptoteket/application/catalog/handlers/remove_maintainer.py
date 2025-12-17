from __future__ import annotations

from skriptoteket.application.catalog.commands import (
    RemoveMaintainerCommand,
    RemoveMaintainerResult,
)
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.catalog import (
    RemoveMaintainerHandlerProtocol,
    ToolMaintainerAuditRepositoryProtocol,
    ToolMaintainerRepositoryProtocol,
    ToolRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import UserRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class RemoveMaintainerHandler(RemoveMaintainerHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        users: UserRepositoryProtocol,
        audit: ToolMaintainerAuditRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._tools = tools
        self._maintainers = maintainers
        self._users = users
        self._audit = audit
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self, *, actor: User, command: RemoveMaintainerCommand
    ) -> RemoveMaintainerResult:
        require_at_least_role(user=actor, role=Role.ADMIN)

        now = self._clock.now()
        log_id = self._id_generator.new_uuid()

        async with self._uow:
            tool = await self._tools.get_by_id(tool_id=command.tool_id)
            if tool is None:
                raise not_found("Tool", str(command.tool_id))

            target_user = await self._users.get_by_id(user_id=command.user_id)
            if target_user is None:
                raise not_found("User", str(command.user_id))

            is_maintainer = await self._maintainers.is_maintainer(
                tool_id=command.tool_id, user_id=command.user_id
            )
            if not is_maintainer:
                raise validation_error(
                    "User is not a maintainer of this tool",
                    details={"tool_id": str(command.tool_id), "user_id": str(command.user_id)},
                )

            await self._maintainers.remove_maintainer(
                tool_id=command.tool_id,
                user_id=command.user_id,
            )

            await self._audit.log_action(
                log_id=log_id,
                tool_id=command.tool_id,
                user_id=command.user_id,
                action="removed",
                performed_by_user_id=actor.id,
                performed_at=now,
                reason=command.reason,
            )

        return RemoveMaintainerResult(
            tool_id=command.tool_id,
            user_id=command.user_id,
        )
