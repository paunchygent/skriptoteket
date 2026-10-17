from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from hashlib import blake2b
from uuid import UUID

from sqlalchemy import asc, desc, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from skriptoteket.domain.scripting.vault import VaultFile, VaultListSort, VaultListState
from skriptoteket.infrastructure.db.models.user_vault_file import (
    ExamWorkspaceHistoryModel,
    UserVaultFileModel,
)
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol


class PostgreSQLUserVaultFileRepository(VaultFileRepositoryProtocol):
    """PostgreSQL repository for user vault files and exam workspace history."""

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
        # A saved exam export is listed with its exam, active or in the trash, and
        # never as its own Mina filer row. The exclusion happens in SQL, before
        # LIMIT/OFFSET, so export rows never consume a page slot.
        stmt = stmt.where(UserVaultFileModel.export_format.is_(None))
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
        """Return the one active exam document row of a lineage, never a saved export."""

        stmt = (
            select(UserVaultFileModel)
            .where(
                UserVaultFileModel.user_id == user_id,
                UserVaultFileModel.document_lineage_id == document_lineage_id,
                UserVaultFileModel.deleted_at.is_(None),
                UserVaultFileModel.export_format.is_(None),
            )
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
        """Return every active exam document row, newest first."""

        stmt = (
            select(UserVaultFileModel)
            .where(
                UserVaultFileModel.user_id == user_id,
                UserVaultFileModel.document_lineage_id.is_not(None),
                UserVaultFileModel.deleted_at.is_(None),
                UserVaultFileModel.export_format.is_(None),
                UserVaultFileModel.source_artifact_id.startswith(
                    source_artifact_prefix, autoescape=True
                ),
            )
            .order_by(
                desc(UserVaultFileModel.created_at),
                desc(UserVaultFileModel.id),
            )
        )
        result = await self._session.execute(stmt)
        return [VaultFile.model_validate(item) for item in result.scalars().all()]

    async def list_saved_exports(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> list[VaultFile]:
        """Return the active saved export of each format for one exam."""

        stmt = (
            select(UserVaultFileModel)
            .where(
                UserVaultFileModel.user_id == user_id,
                UserVaultFileModel.document_lineage_id == document_lineage_id,
                UserVaultFileModel.deleted_at.is_(None),
                UserVaultFileModel.export_format.is_not(None),
            )
            .order_by(asc(UserVaultFileModel.export_format), asc(UserVaultFileModel.id))
        )
        result = await self._session.execute(stmt)
        return [VaultFile.model_validate(item) for item in result.scalars().all()]

    async def list_exam_files(
        self,
        *,
        user_id: UUID,
        document_lineage_id: UUID,
        include_deleted: bool,
    ) -> list[VaultFile]:
        """Return the stored rows of one exam: its document row and saved exports.

        The exam's saved exports belong to the exam, so its lifecycle and its Mina
        filer listing read them together with it: the active rows, or, with
        ``include_deleted``, the rows in the trash as well. The exam document row
        comes first, then its exports by format.
        """

        stmt = (
            select(UserVaultFileModel)
            .where(
                UserVaultFileModel.user_id == user_id,
                UserVaultFileModel.document_lineage_id == document_lineage_id,
            )
            .order_by(
                asc(UserVaultFileModel.export_format).nulls_first(),
                asc(UserVaultFileModel.created_at),
                asc(UserVaultFileModel.id),
            )
        )
        if not include_deleted:
            stmt = stmt.where(UserVaultFileModel.deleted_at.is_(None))

        result = await self._session.execute(stmt)
        return [VaultFile.model_validate(item) for item in result.scalars().all()]

    async def get_history(self, *, user_id: UUID, document_lineage_id: UUID) -> bytes | None:
        result = await self._session.execute(
            select(ExamWorkspaceHistoryModel.content).where(
                ExamWorkspaceHistoryModel.user_id == user_id,
                ExamWorkspaceHistoryModel.lineage_id == document_lineage_id,
            )
        )
        return result.scalar_one_or_none()

    async def put_history(
        self, *, user_id: UUID, document_lineage_id: UUID, content: bytes
    ) -> None:
        await self._session.execute(
            pg_insert(ExamWorkspaceHistoryModel)
            .values(user_id=user_id, lineage_id=document_lineage_id, content=content)
            .on_conflict_do_update(
                index_elements=["user_id", "lineage_id"],
                set_={"content": content},
            )
        )

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

    async def _lock(self, *, key: str) -> None:
        # Stable, namespaced signed bigint; locks last until the owning UoW ends.
        lock_id = int.from_bytes(blake2b(key.encode(), digest_size=8).digest(), signed=True)
        await self._session.execute(select(func.pg_advisory_xact_lock(lock_id)))

    async def lock_owner_renames(self, *, user_id: UUID) -> None:
        await self._lock(key=f"vault:rename-owner:{user_id}")

    @asynccontextmanager
    async def guard_document_payload(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> AsyncIterator[None]:
        # An independent, rollback-only connection retains this lock even when
        # the application COMMIT fails and releases its transaction locks.
        bind = self._session.bind
        if bind is None:
            raise RuntimeError("A payload guard requires a bound database engine.")
        engine = bind.engine if isinstance(bind, AsyncConnection) else bind
        key = f"vault:payload:{user_id}:{document_lineage_id}"
        lock_id = int.from_bytes(blake2b(key.encode(), digest_size=8).digest(), signed=True)
        # Requests may already hold their application-pool connection (e.g. auth).
        # A second checkout from that same bounded pool can deadlock every writer
        # when the pool is full. Guard connections are short-lived and unpooled.
        guard_engine = create_async_engine(engine.url, poolclass=NullPool)
        try:
            async with guard_engine.connect() as connection:
                await connection.execute(select(func.pg_advisory_xact_lock(lock_id)))
                yield
            # Connection.close rolls back; repositories never commit application data.
        finally:
            await guard_engine.dispose()

    async def lock_document_lineage(self, *, user_id: UUID, document_lineage_id: UUID) -> None:
        await self._lock(key=f"vault:lineage:{user_id}:{document_lineage_id}")

    async def lock_lifecycle_rows(
        self,
        *,
        user_id: UUID,
        file_id: UUID,
        document_lineage_id: UUID | None,
    ) -> list[VaultFile]:
        """Return fresh lineage rows, or the plain file, locked in UUID order.

        Callers must hold the lineage lock when a lineage is present and acquire
        usage locks afterward. Row locks remain held until the Unit of Work ends.
        """
        stmt = select(UserVaultFileModel).where(UserVaultFileModel.user_id == user_id)
        if document_lineage_id is not None:
            stmt = stmt.where(UserVaultFileModel.document_lineage_id == document_lineage_id)
        else:
            stmt = stmt.where(UserVaultFileModel.id == file_id)
        stmt = (
            stmt.order_by(asc(UserVaultFileModel.id))
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        result = await self._session.execute(stmt)
        return [VaultFile.model_validate(item) for item in result.scalars().all()]

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
        """Rename the exam document row of a lineage; saved exports keep their own names."""

        result = await self._session.execute(
            update(UserVaultFileModel)
            .where(
                UserVaultFileModel.user_id == user_id,
                UserVaultFileModel.document_lineage_id == document_lineage_id,
                UserVaultFileModel.export_format.is_(None),
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
            export_format=file.export_format,
            document_saved_at=file.document_saved_at,
            created_at=file.created_at,
            deleted_at=file.deleted_at,
            trashed_with_exam=file.trashed_with_exam,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return VaultFile.model_validate(model)

    async def update(self, *, file: VaultFile) -> VaultFile:
        """Change lifecycle state without replaying stale names or content metadata."""
        model = await self._session.get(UserVaultFileModel, file.id, populate_existing=True)
        if model is None:
            return file
        model.deleted_at = file.deleted_at
        model.trashed_with_exam = file.trashed_with_exam
        await self._session.flush()
        await self._session.refresh(model)
        return VaultFile.model_validate(model)

    async def overwrite(self, *, file: VaultFile) -> VaultFile:
        """Write the mutable payload of one stored file.

        Callers hold the lineage lock and replace content accounting and revision.
        Lifecycle state is deliberately preserved; ``update`` owns trash and restore.
        """

        model = await self._session.get(UserVaultFileModel, file.id)
        if model is None:
            return file

        model.name = file.name
        model.bytes = file.bytes
        model.source_artifact_id = file.source_artifact_id
        model.document_version = file.document_version
        model.export_format = file.export_format
        model.document_saved_at = file.document_saved_at

        await self._session.flush()
        await self._session.refresh(model)
        return VaultFile.model_validate(model)

    async def delete(self, *, file_id: UUID) -> None:
        """Purge one row and, for an exam document row, its undo history.

        The caller owns the group: saved export rows belong to their exam, so a
        permanent exam purge deletes every linked row and commits before it deletes
        any payload file. A failed file delete is logged and leaves an orphaned file,
        never a row without its file. This method deletes exactly the row it was
        given, so a purge never drops a sibling row the caller did not select.
        """

        model = await self._session.get(UserVaultFileModel, file_id)
        if model is None:
            return
        if model.document_lineage_id is not None and model.export_format is None:
            history = await self._session.get(
                ExamWorkspaceHistoryModel, (model.user_id, model.document_lineage_id)
            )
            if history is not None:
                await self._session.delete(history)
        await self._session.delete(model)
        await self._session.flush()
