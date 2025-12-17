from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.infrastructure.db.models.tool_maintainer_audit_log import (
    MaintainerAuditAction,
    ToolMaintainerAuditLogModel,
)


class PostgreSQLToolMaintainerAuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log_action(
        self,
        *,
        log_id: UUID,
        tool_id: UUID,
        user_id: UUID,
        action: str,
        performed_by_user_id: UUID,
        performed_at: datetime,
        reason: str | None,
    ) -> None:
        self._session.add(
            ToolMaintainerAuditLogModel(
                id=log_id,
                tool_id=tool_id,
                user_id=user_id,
                action=action,
                performed_by_user_id=performed_by_user_id,
                performed_at=performed_at,
                reason=reason,
            )
        )
        await self._session.flush()

    async def log_assignment(
        self,
        *,
        log_id: UUID,
        tool_id: UUID,
        user_id: UUID,
        performed_by_user_id: UUID,
        performed_at: datetime,
        reason: str | None,
    ) -> None:
        await self.log_action(
            log_id=log_id,
            tool_id=tool_id,
            user_id=user_id,
            action=MaintainerAuditAction.ASSIGNED.value,
            performed_by_user_id=performed_by_user_id,
            performed_at=performed_at,
            reason=reason,
        )

    async def log_removal(
        self,
        *,
        log_id: UUID,
        tool_id: UUID,
        user_id: UUID,
        performed_by_user_id: UUID,
        performed_at: datetime,
        reason: str | None,
    ) -> None:
        await self.log_action(
            log_id=log_id,
            tool_id=tool_id,
            user_id=user_id,
            action=MaintainerAuditAction.REMOVED.value,
            performed_by_user_id=performed_by_user_id,
            performed_at=performed_at,
            reason=reason,
        )
