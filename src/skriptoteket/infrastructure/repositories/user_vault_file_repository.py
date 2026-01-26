from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.scripting.vault import VaultFile, VaultListSort, VaultListState
from skriptoteket.infrastructure.db.models.user_vault_file import UserVaultFileModel
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol


class PostgreSQLUserVaultFileRepository(VaultFileRepositoryProtocol):
    """PostgreSQL repository for user vault files."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, *, file_id: UUID) -> VaultFile | None:
        model = await self._session.get(UserVaultFileModel, file_id)
        return VaultFile.model_validate(model) if model else None

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        state: VaultListState,
        search: str | None,
        sort: VaultListSort,
        limit: int,
        offset: int,
    ) -> list[VaultFile]:
        stmt = select(UserVaultFileModel).where(UserVaultFileModel.user_id == user_id)
        if state is VaultListState.ACTIVE:
            stmt = stmt.where(UserVaultFileModel.deleted_at.is_(None))
        else:
            stmt = stmt.where(UserVaultFileModel.deleted_at.is_not(None))

        if search:
            stmt = stmt.where(UserVaultFileModel.name.ilike(f"%{search}%"))

        if sort is VaultListSort.NAME:
            stmt = stmt.order_by(
                asc(func.lower(UserVaultFileModel.name)),
                asc(UserVaultFileModel.id),
            )
        elif sort is VaultListSort.SIZE:
            stmt = stmt.order_by(desc(UserVaultFileModel.bytes), desc(UserVaultFileModel.id))
        else:
            stmt = stmt.order_by(desc(UserVaultFileModel.created_at), desc(UserVaultFileModel.id))

        stmt = stmt.offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return [VaultFile.model_validate(item) for item in result.scalars().all()]

    async def list_active_for_user(self, *, user_id: UUID) -> list[VaultFile]:
        stmt = (
            select(UserVaultFileModel)
            .where(UserVaultFileModel.user_id == user_id)
            .where(UserVaultFileModel.deleted_at.is_(None))
            .order_by(desc(UserVaultFileModel.created_at), desc(UserVaultFileModel.id))
        )
        result = await self._session.execute(stmt)
        return [VaultFile.model_validate(item) for item in result.scalars().all()]

    async def list_by_ids(
        self,
        *,
        user_id: UUID,
        file_ids: list[UUID],
        include_deleted: bool,
    ) -> list[VaultFile]:
        if not file_ids:
            return []

        stmt = select(UserVaultFileModel).where(
            UserVaultFileModel.user_id == user_id,
            UserVaultFileModel.id.in_(file_ids),
        )
        if not include_deleted:
            stmt = stmt.where(UserVaultFileModel.deleted_at.is_(None))

        result = await self._session.execute(stmt)
        return [VaultFile.model_validate(item) for item in result.scalars().all()]

    async def list_expired(
        self,
        *,
        cutoff: datetime,
        limit: int,
    ) -> list[VaultFile]:
        stmt = (
            select(UserVaultFileModel)
            .where(UserVaultFileModel.deleted_at.is_not(None))
            .where(UserVaultFileModel.deleted_at < cutoff)
            .order_by(asc(UserVaultFileModel.deleted_at), asc(UserVaultFileModel.id))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [VaultFile.model_validate(item) for item in result.scalars().all()]

    async def create(self, *, file: VaultFile) -> VaultFile:
        model = UserVaultFileModel(
            id=file.id,
            user_id=file.user_id,
            name=file.name,
            bytes=file.bytes,
            source_kind=file.source_kind.value,
            source_run_id=file.source_run_id,
            source_artifact_id=file.source_artifact_id,
            created_at=file.created_at,
            deleted_at=file.deleted_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return VaultFile.model_validate(model)

    async def update(self, *, file: VaultFile) -> VaultFile:
        model = await self._session.get(UserVaultFileModel, file.id)
        if model is None:
            return file

        model.name = file.name
        model.bytes = file.bytes
        model.source_kind = file.source_kind.value
        model.source_run_id = file.source_run_id
        model.source_artifact_id = file.source_artifact_id
        model.created_at = file.created_at
        model.deleted_at = file.deleted_at

        await self._session.flush()
        await self._session.refresh(model)
        return VaultFile.model_validate(model)

    async def delete(self, *, file_id: UUID) -> None:
        model = await self._session.get(UserVaultFileModel, file_id)
        if model is None:
            return
        await self._session.delete(model)
        await self._session.flush()
