from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.scripting.vault import VaultUsage
from skriptoteket.infrastructure.db.models.user_vault_file import UserVaultFileModel
from skriptoteket.infrastructure.db.models.user_vault_usage import UserVaultUsageModel
from skriptoteket.protocols.vault import VaultUsageRepositoryProtocol


class PostgreSQLUserVaultUsageRepository(VaultUsageRepositoryProtocol):
    """PostgreSQL repository for per-user vault usage totals."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, *, user_id: UUID) -> VaultUsage | None:
        result = await self._session.execute(
            select(UserVaultUsageModel).where(UserVaultUsageModel.user_id == user_id)
        )
        model = result.scalar_one_or_none()
        return VaultUsage.model_validate(model) if model else None

    async def get_for_update(self, *, user_id: UUID, now: datetime) -> VaultUsage:
        await self._session.execute(
            insert(UserVaultUsageModel)
            .values(user_id=user_id, bytes_total=0, updated_at=now)
            .on_conflict_do_nothing(index_elements=["user_id"])
        )
        result = await self._session.execute(
            select(UserVaultUsageModel)
            .where(UserVaultUsageModel.user_id == user_id)
            .with_for_update()
        )
        model = result.scalar_one()
        return VaultUsage.model_validate(model)

    async def upsert(self, *, usage: VaultUsage) -> VaultUsage:
        model = await self._session.get(UserVaultUsageModel, usage.user_id)
        if model is None:
            model = UserVaultUsageModel(
                user_id=usage.user_id,
                bytes_total=usage.bytes_total,
                updated_at=usage.updated_at,
            )
            self._session.add(model)
        else:
            model.bytes_total = usage.bytes_total
            model.updated_at = usage.updated_at
        await self._session.flush()
        await self._session.refresh(model)
        return VaultUsage.model_validate(model)

    async def recompute_total(self, *, user_id: UUID, now: datetime) -> int:
        result = await self._session.execute(
            select(func.coalesce(func.sum(UserVaultFileModel.bytes), 0)).where(
                UserVaultFileModel.user_id == user_id,
                UserVaultFileModel.deleted_at.is_(None),
            )
        )
        total_bytes = int(result.scalar_one() or 0)
        usage = await self.get_for_update(user_id=user_id, now=now)
        await self.upsert(
            usage=VaultUsage(
                user_id=usage.user_id,
                bytes_total=total_bytes,
                updated_at=now,
            )
        )
        return total_bytes
