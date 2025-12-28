from __future__ import annotations

from datetime import timedelta

from skriptoteket.application.scripting.draft_locks import (
    AcquireDraftLockCommand,
    AcquireDraftLockResult,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.domain.scripting.draft_locks import DraftLock
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.draft_locks import (
    AcquireDraftLockHandlerProtocol,
    DraftLockRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class AcquireDraftLockHandler(AcquireDraftLockHandlerProtocol):
    """Acquire or refresh a draft head lock (ST-14-07)."""

    def __init__(
        self,
        *,
        settings: Settings,
        uow: UnitOfWorkProtocol,
        locks: DraftLockRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._settings = settings
        self._uow = uow
        self._locks = locks
        self._clock = clock

    async def handle(
        self,
        *,
        actor: User,
        command: AcquireDraftLockCommand,
    ) -> AcquireDraftLockResult:
        require_at_least_role(user=actor, role=Role.CONTRIBUTOR)

        now = self._clock.now()
        expires_at = now + timedelta(seconds=self._settings.DRAFT_LOCK_TTL_SECONDS)

        async with self._uow:
            existing = await self._locks.get_for_tool(tool_id=command.tool_id)

            if (
                existing is not None
                and existing.expires_at > now
                and existing.locked_by_user_id != actor.id
            ):
                if not command.force:
                    raise DomainError(
                        code=ErrorCode.FORBIDDEN,
                        message="Draft lock is held by another user",
                        details={
                            "tool_id": str(command.tool_id),
                            "locked_by_user_id": str(existing.locked_by_user_id),
                            "expires_at": existing.expires_at.isoformat(),
                        },
                    )

                if actor.role not in {Role.ADMIN, Role.SUPERUSER}:
                    raise DomainError(
                        code=ErrorCode.FORBIDDEN,
                        message="Force takeover requires admin access",
                        details={"tool_id": str(command.tool_id)},
                    )

            forced_by_user_id = (
                actor.id
                if existing is not None and existing.locked_by_user_id != actor.id and command.force
                else None
            )

            saved = await self._locks.upsert(
                lock=DraftLock(
                    tool_id=command.tool_id,
                    draft_head_id=command.draft_head_id,
                    locked_by_user_id=actor.id,
                    locked_at=now,
                    expires_at=expires_at,
                    forced_by_user_id=forced_by_user_id,
                )
            )

        return AcquireDraftLockResult(
            tool_id=saved.tool_id,
            draft_head_id=saved.draft_head_id,
            locked_by_user_id=saved.locked_by_user_id,
            expires_at=saved.expires_at,
            is_owner=saved.locked_by_user_id == actor.id,
        )
