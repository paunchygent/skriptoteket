from __future__ import annotations

from datetime import datetime
from uuid import UUID

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.draft_locks import DraftLock
from skriptoteket.protocols.draft_locks import DraftLockRepositoryProtocol


async def require_active_draft_lock(
    *,
    locks: DraftLockRepositoryProtocol,
    tool_id: UUID,
    draft_head_id: UUID,
    actor: User,
    now: datetime,
) -> DraftLock:
    lock = await locks.get_for_tool(tool_id=tool_id)
    if lock is None:
        raise DomainError(
            code=ErrorCode.CONFLICT,
            message="Draft lock is required",
            details={"tool_id": str(tool_id), "draft_head_id": str(draft_head_id)},
        )

    if lock.expires_at <= now:
        raise DomainError(
            code=ErrorCode.CONFLICT,
            message="Draft lock has expired",
            details={
                "tool_id": str(tool_id),
                "draft_head_id": str(draft_head_id),
                "locked_by_user_id": str(lock.locked_by_user_id),
                "expires_at": lock.expires_at.isoformat(),
            },
        )

    if lock.locked_by_user_id != actor.id:
        raise DomainError(
            code=ErrorCode.FORBIDDEN,
            message="Draft lock is held by another user",
            details={
                "tool_id": str(tool_id),
                "draft_head_id": str(draft_head_id),
                "locked_by_user_id": str(lock.locked_by_user_id),
                "expires_at": lock.expires_at.isoformat(),
            },
        )

    if lock.draft_head_id != draft_head_id:
        raise DomainError(
            code=ErrorCode.CONFLICT,
            message="Draft lock does not match current draft head",
            details={
                "tool_id": str(tool_id),
                "draft_head_id": str(draft_head_id),
                "lock_draft_head_id": str(lock.draft_head_id),
            },
        )

    return lock
