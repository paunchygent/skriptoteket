from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.scripting.sandbox_snapshots import SandboxSnapshot
from skriptoteket.infrastructure.db.models.sandbox_snapshot import SandboxSnapshotModel
from skriptoteket.protocols.sandbox_snapshots import SandboxSnapshotRepositoryProtocol


class PostgreSQLSandboxSnapshotRepository(SandboxSnapshotRepositoryProtocol):
    """PostgreSQL repository for sandbox snapshots.

    Uses a request-scoped AsyncSession; commit/rollback is owned by the Unit of Work.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, *, snapshot_id: UUID) -> SandboxSnapshot | None:
        stmt = select(SandboxSnapshotModel).where(SandboxSnapshotModel.id == snapshot_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return SandboxSnapshot.model_validate(model)

    async def create(self, *, snapshot: SandboxSnapshot) -> SandboxSnapshot:
        settings_schema = (
            None
            if snapshot.settings_schema is None
            else [field.model_dump(mode="json") for field in snapshot.settings_schema]
        )
        input_schema = (
            None
            if snapshot.input_schema is None
            else [field.model_dump(mode="json") for field in snapshot.input_schema]
        )
        model = SandboxSnapshotModel(
            id=snapshot.id,
            tool_id=snapshot.tool_id,
            draft_head_id=snapshot.draft_head_id,
            created_by_user_id=snapshot.created_by_user_id,
            entrypoint=snapshot.entrypoint,
            source_code=snapshot.source_code,
            settings_schema=settings_schema,
            input_schema=input_schema,
            usage_instructions=snapshot.usage_instructions,
            payload_bytes=snapshot.payload_bytes,
            created_at=snapshot.created_at,
            expires_at=snapshot.expires_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return SandboxSnapshot.model_validate(model)

    async def delete_expired(self, *, now: datetime) -> int:
        stmt = delete(SandboxSnapshotModel).where(SandboxSnapshotModel.expires_at <= now)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return int(cast(CursorResult[Any], result).rowcount or 0)
