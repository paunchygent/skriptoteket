from __future__ import annotations

from skriptoteket.application.scripting.draft_locks import (
    ReleaseDraftLockCommand,
    ReleaseDraftLockResult,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.draft_locks import (
    DraftLockRepositoryProtocol,
    ReleaseDraftLockHandlerProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class ReleaseDraftLockHandler(ReleaseDraftLockHandlerProtocol):
    """Release a draft head lock (ST-14-07)."""

    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        locks: DraftLockRepositoryProtocol,
    ) -> None:
        self._uow = uow
        self._locks = locks

    async def handle(
        self,
        *,
        actor: User,
        command: ReleaseDraftLockCommand,
    ) -> ReleaseDraftLockResult:
        require_at_least_role(user=actor, role=Role.CONTRIBUTOR)

        async with self._uow:
            existing = await self._locks.get_for_tool(tool_id=command.tool_id)
            if existing is None:
                raise not_found("DraftLock", str(command.tool_id))

            if existing.locked_by_user_id != actor.id and actor.role not in {
                Role.ADMIN,
                Role.SUPERUSER,
            }:
                raise DomainError(
                    code=ErrorCode.FORBIDDEN,
                    message="Cannot release another user's draft lock",
                    details={"tool_id": str(command.tool_id)},
                )

            await self._locks.delete(tool_id=command.tool_id)

        return ReleaseDraftLockResult(tool_id=command.tool_id)
