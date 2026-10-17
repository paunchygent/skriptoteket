"""Permanent vault deletion purges a trashed exam's exports, history, payloads and bytes.

The runner end to end against PostgreSQL and the filesystem: after the cleanup the exam
and its saved exports are gone as rows and as files, the exam history is gone, the live
exam beside them is untouched, and the user's byte total is recomputed from the rows
that remain instead of subtracting already released trash bytes again.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.cli.commands.cleanup_vault_files import (
    open_vault_cleanup_scope,
    purge_expired_vault_files,
)
from skriptoteket.domain.identity.models import AuthProvider, Role
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind, VaultUsage
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.repositories.user_vault_file_repository import (
    PostgreSQLUserVaultFileRepository,
)
from skriptoteket.infrastructure.repositories.user_vault_usage_repository import (
    PostgreSQLUserVaultUsageRepository,
)
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage

pytestmark = [
    pytest.mark.integration,
    pytest.mark.docker,
    pytest.mark.asyncio(loop_scope="module"),
]
_NOW = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)
_CUTOFF = _NOW - timedelta(days=30)


async def _owner(session: AsyncSession) -> UUID:
    user_id = uuid4()
    session.add(
        UserModel(
            id=user_id,
            email=f"cleanup-linked-{user_id}@example.com",
            password_hash="hash",
            role=Role.USER,
            auth_provider=AuthProvider.LOCAL,
            created_at=_NOW,
            updated_at=_NOW,
        )
    )
    await session.flush()
    return user_id


def _file(user_id: UUID, *, name: str, file_bytes: int, **updates: object) -> VaultFile:
    return VaultFile(
        id=uuid4(),
        user_id=user_id,
        name=name,
        bytes=file_bytes,
        source_kind=VaultFileSourceKind.APP_EXPORT,
        created_at=_NOW - timedelta(days=60),
    ).model_copy(update=updates)


def _exam(user_id: UUID, *, lineage_id: UUID, file_bytes: int, **updates: object) -> VaultFile:
    return _file(
        user_id,
        name="Prov.provdokument.zip",
        file_bytes=file_bytes,
        document_lineage_id=lineage_id,
        document_version=1,
        **updates,
    )


def _export(
    user_id: UUID,
    *,
    lineage_id: UUID,
    export_format: str,
    file_bytes: int,
    **updates: object,
) -> VaultFile:
    return _file(
        user_id,
        name=f"Prov-{export_format}.zip",
        file_bytes=file_bytes,
        document_lineage_id=lineage_id,
        document_version=1,
        export_format=export_format,
        **updates,
    )


async def test_purge_deletes_the_trashed_exam_with_its_exports_history_payloads_and_bytes(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    async with session_factory() as session:
        vault_files = PostgreSQLUserVaultFileRepository(session)
        vault_usage = PostgreSQLUserVaultUsageRepository(session)
        storage = LocalVaultStorage(vault_root=tmp_path / "vault")
        owner = await _owner(session)
        trashed_at = _CUTOFF - timedelta(days=1)
        lineage = uuid4()
        exam = _exam(owner, lineage_id=lineage, file_bytes=100, deleted_at=trashed_at)
        qti = _export(
            owner, lineage_id=lineage, export_format="qti", file_bytes=10, deleted_at=trashed_at
        )
        pdf = _export(
            owner, lineage_id=lineage, export_format="pdf", file_bytes=20, deleted_at=trashed_at
        )
        # An export restored on its own while the exam sat in the trash is active again,
        # and an export trashed after the exam is still inside its own window: a
        # permanent deletion of the exam takes both, whatever state they are in.
        orphan_docx = _export(owner, lineage_id=lineage, export_format="docx", file_bytes=30)
        later_zip = _export(
            owner,
            lineage_id=lineage,
            export_format="zip",
            file_bytes=40,
            deleted_at=_NOW - timedelta(days=5),
        )
        live_lineage = uuid4()
        live_exam = _exam(owner, lineage_id=live_lineage, file_bytes=100)
        purged = (exam, qti, pdf, orphan_docx, later_zip)
        for row in (*purged, live_exam):
            await vault_files.create(file=row)
            await storage.store_file(user_id=owner, file_id=row.id, content=b"payload")
        await vault_files.put_history(
            user_id=owner, document_lineage_id=lineage, content=b"exam history"
        )
        await vault_files.put_history(
            user_id=owner, document_lineage_id=live_lineage, content=b"live history"
        )
        # The exam's trashed bytes were released when it moved to the trash, so the user's
        # total counts the live exam and the active orphan export.
        await vault_usage.upsert(
            usage=VaultUsage(
                user_id=owner,
                bytes_total=live_exam.bytes + orphan_docx.bytes,
                updated_at=trashed_at,
            )
        )

        async with SQLAlchemyUnitOfWork(session):
            pass  # Publish setup before cleanup opens its independent group sessions.

        deleted, affected_users = await purge_expired_vault_files(
            scope_factory=partial(open_vault_cleanup_scope, session_factory),
            storage=storage,
            cutoff=_CUTOFF,
            now=_NOW,
        )

        session.expire_all()
        assert deleted == 5
        assert affected_users == {owner}
        for row in purged:
            assert await vault_files.get_by_id(file_id=row.id) is None
            assert not await storage.exists_file(user_id=owner, file_id=row.id)
        assert await vault_files.get_history(user_id=owner, document_lineage_id=lineage) is None
        assert await vault_files.get_by_id(file_id=live_exam.id) is not None
        assert await storage.exists_file(user_id=owner, file_id=live_exam.id)
        assert (
            await vault_files.get_history(user_id=owner, document_lineage_id=live_lineage)
            == b"live history"
        )
        usage = await vault_usage.get(user_id=owner)
        assert usage is not None
        assert usage.bytes_total == live_exam.bytes
