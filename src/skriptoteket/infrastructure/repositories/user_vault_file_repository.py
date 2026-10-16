from __future__ import annotations

from datetime import datetime
from hashlib import blake2b
from uuid import UUID

from sqlalchemy import asc, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.scripting.vault import VaultFile, VaultListSort, VaultListState
from skriptoteket.infrastructure.db.models.user_vault_file import UserVaultFileModel
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol


class PostgreSQLUserVaultFileRepository(VaultFileRepositoryProtocol):
    """PostgreSQL repository for user vault files."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, *, file_id: UUID) -> VaultFile | None:
        model = await self._session.get(UserVaultFileModel, file_id, populate_existing=True)
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

    async def get_document_head(
        self,
        *,
        user_id: UUID,
        document_lineage_id: UUID,
    ) -> VaultFile | None:
        stmt = (
            select(UserVaultFileModel)
            .where(UserVaultFileModel.user_id == user_id)
            .where(UserVaultFileModel.document_lineage_id == document_lineage_id)
            .where(UserVaultFileModel.deleted_at.is_(None))
            .order_by(desc(UserVaultFileModel.document_version))
            .limit(1)
            .execution_options(populate_existing=True)
        )
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        return VaultFile.model_validate(model) if model else None

    async def list_document_heads(
        self,
        *,
        user_id: UUID,
        source_artifact_prefix: str,
    ) -> list[VaultFile]:
        """Return the newest active version per document lineage, newest first."""

        stmt = (
            select(UserVaultFileModel)
            .where(UserVaultFileModel.user_id == user_id)
            .where(UserVaultFileModel.document_lineage_id.is_not(None))
            .where(UserVaultFileModel.deleted_at.is_(None))
            .where(
                UserVaultFileModel.source_artifact_id.startswith(
                    source_artifact_prefix, autoescape=True
                )
            )
            .distinct(UserVaultFileModel.document_lineage_id)
            .order_by(
                UserVaultFileModel.document_lineage_id,
                desc(UserVaultFileModel.document_version),
            )
        )
        result = await self._session.execute(stmt)
        heads = [VaultFile.model_validate(item) for item in result.scalars().all()]
        return sorted(heads, key=lambda file: (file.created_at, file.id), reverse=True)

    async def name_in_use(
        self,
        *,
        user_id: UUID,
        name: str,
        exclude_lineage_id: UUID | None,
        exclude_file_id: UUID | None,
    ) -> bool:
        stmt = select(UserVaultFileModel.id).where(
            UserVaultFileModel.user_id == user_id,
            UserVaultFileModel.name == name,
            UserVaultFileModel.deleted_at.is_(None),
        )
        if exclude_lineage_id is not None:
            stmt = stmt.where(
                or_(
                    UserVaultFileModel.document_lineage_id.is_(None),
                    UserVaultFileModel.document_lineage_id != exclude_lineage_id,
                )
            )
        if exclude_file_id is not None:
            stmt = stmt.where(UserVaultFileModel.id != exclude_file_id)
        result = await self._session.execute(select(stmt.exists()))
        return bool(result.scalar_one())

    async def list_lineage_versions(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> list[VaultFile]:
        stmt = (
            select(UserVaultFileModel)
            .where(
                UserVaultFileModel.user_id == user_id,
                UserVaultFileModel.document_lineage_id == document_lineage_id,
            )
            .order_by(asc(UserVaultFileModel.document_version), asc(UserVaultFileModel.id))
        )
        result = await self._session.execute(stmt)
        return [VaultFile.model_validate(item) for item in result.scalars().all()]

    async def _lock(self, *, key: str) -> None:
        # Stable, namespaced signed bigint; locks last until the owning UoW ends.
        lock_id = int.from_bytes(blake2b(key.encode(), digest_size=8).digest(), signed=True)
        await self._session.execute(select(func.pg_advisory_xact_lock(lock_id)))

    async def lock_owner_renames(self, *, user_id: UUID) -> None:
        await self._lock(key=f"vault:rename-owner:{user_id}")

    async def lock_document_lineage(self, *, user_id: UUID, document_lineage_id: UUID) -> None:
        await self._lock(key=f"vault:lineage:{user_id}:{document_lineage_id}")

    async def rename_active(self, *, user_id: UUID, file_id: UUID, name: str) -> VaultFile | None:
        result = await self._session.execute(
            update(UserVaultFileModel)
            .where(
                UserVaultFileModel.id == file_id,
                UserVaultFileModel.user_id == user_id,
                UserVaultFileModel.deleted_at.is_(None),
            )
            .values(name=name)
            .returning(UserVaultFileModel)
            .execution_options(populate_existing=True)
        )
        model = result.scalar_one_or_none()
        return VaultFile.model_validate(model) if model is not None else None

    async def rename_lineage(
        self, *, user_id: UUID, document_lineage_id: UUID, name: str
    ) -> list[VaultFile]:
        result = await self._session.execute(
            update(UserVaultFileModel)
            .where(
                UserVaultFileModel.user_id == user_id,
                UserVaultFileModel.document_lineage_id == document_lineage_id,
            )
            .values(name=name)
            .returning(UserVaultFileModel)
            .execution_options(populate_existing=True)
        )
        return [VaultFile.model_validate(model) for model in result.scalars().all()]

    async def create(self, *, file: VaultFile) -> VaultFile:
        model = UserVaultFileModel(
            id=file.id,
            user_id=file.user_id,
            name=file.name,
            bytes=file.bytes,
            source_kind=file.source_kind.value,
            source_run_id=file.source_run_id,
            source_artifact_id=file.source_artifact_id,
            document_lineage_id=file.document_lineage_id,
            document_version=file.document_version,
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

        # Lifecycle callers own only trash state. A stale delete/restore payload
        # must not overwrite a concurrently committed name or immutable metadata.
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
