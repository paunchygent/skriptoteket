"""The Mina filer repository keeps a saved export with its exam.

An export row is never a page row in either state, the lineage query returns the exam
document row before its exports and can include the trash, and purging a row purges the
exam history only for the exam document row.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.domain.identity.models import AuthProvider, Role
from skriptoteket.domain.scripting.vault import (
    VaultFile,
    VaultFileSourceKind,
    VaultListSort,
    VaultListState,
)
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.repositories.user_vault_file_repository import (
    PostgreSQLUserVaultFileRepository,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.docker,
    pytest.mark.asyncio(loop_scope="module"),
]
_NOW = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)


async def _owner(session: AsyncSession) -> UUID:
    user_id = uuid4()
    session.add(
        UserModel(
            id=user_id,
            email=f"linked-exports-{user_id}@example.com",
            password_hash="hash",
            role=Role.USER,
            auth_provider=AuthProvider.LOCAL,
            created_at=_NOW,
            updated_at=_NOW,
        )
    )
    await session.flush()
    return user_id


def _file(user_id: UUID, **updates: object) -> VaultFile:
    return VaultFile(
        id=uuid4(),
        user_id=user_id,
        name="Vanlig.pdf",
        bytes=42,
        source_kind=VaultFileSourceKind.APP_EXPORT,
        created_at=_NOW,
    ).model_copy(update=updates)


def _exam(user_id: UUID, *, lineage_id: UUID, **updates: object) -> VaultFile:
    return _file(
        user_id,
        name="Prov.provdokument.zip",
        document_lineage_id=lineage_id,
        document_version=1,
        **updates,
    )


def _export(user_id: UUID, *, lineage_id: UUID, export_format: str, **updates: object) -> VaultFile:
    return _file(
        user_id,
        name=f"Prov-{export_format}.zip",
        document_lineage_id=lineage_id,
        document_version=1,
        export_format=export_format,
        **updates,
    )


async def _page(
    repo: PostgreSQLUserVaultFileRepository,
    *,
    user_id: UUID,
    state: VaultListState,
    limit: int = 50,
    offset: int = 0,
) -> list[VaultFile]:
    return await repo.list_for_user(
        user_id=user_id,
        state=state,
        search=None,
        sort=VaultListSort.NEWEST,
        limit=limit,
        offset=offset,
    )


async def test_list_for_user_excludes_saved_exports_in_both_states_before_paging(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = PostgreSQLUserVaultFileRepository(session)
        owner = await _owner(session)
        active_lineage = uuid4()
        trashed_lineage = uuid4()
        trashed_at = _NOW - timedelta(days=1)
        rows = [
            _file(owner, name="Vanlig.pdf", created_at=_NOW - timedelta(minutes=5)),
            _exam(owner, lineage_id=active_lineage, created_at=_NOW - timedelta(minutes=4)),
            _export(
                owner,
                lineage_id=active_lineage,
                export_format="qti",
                created_at=_NOW - timedelta(minutes=3),
            ),
            _file(
                owner,
                name="Slängd.pdf",
                created_at=_NOW - timedelta(minutes=2),
                deleted_at=trashed_at,
            ),
            _exam(
                owner,
                lineage_id=trashed_lineage,
                created_at=_NOW - timedelta(minutes=1),
                deleted_at=trashed_at,
            ),
            _export(
                owner,
                lineage_id=trashed_lineage,
                export_format="qti",
                created_at=_NOW,
                deleted_at=trashed_at,
            ),
        ]
        for row in rows:
            await repo.create(file=row)

        active = await _page(repo, user_id=owner, state=VaultListState.ACTIVE)
        assert [row.name for row in active] == ["Prov.provdokument.zip", "Vanlig.pdf"]

        # Export rows are excluded in SQL, before LIMIT/OFFSET: consecutive one-row
        # pages hold whole exams and never come back short.
        first_page = await _page(repo, user_id=owner, state=VaultListState.ACTIVE, limit=1)
        second_page = await _page(
            repo, user_id=owner, state=VaultListState.ACTIVE, limit=1, offset=1
        )
        assert [row.name for row in first_page] == ["Prov.provdokument.zip"]
        assert [row.name for row in second_page] == ["Vanlig.pdf"]

        trash = await _page(repo, user_id=owner, state=VaultListState.TRASH)
        assert [row.name for row in trash] == ["Prov.provdokument.zip", "Slängd.pdf"]
        await session.rollback()


async def test_list_exam_files_returns_the_document_row_first_and_filters_the_trash(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = PostgreSQLUserVaultFileRepository(session)
        owner = await _owner(session)
        other_owner = await _owner(session)
        lineage = uuid4()
        other_lineage = uuid4()
        trashed_at = _NOW - timedelta(days=1)
        for row in [
            _exam(owner, lineage_id=lineage),
            _export(owner, lineage_id=lineage, export_format="qti"),
            _export(
                owner,
                lineage_id=lineage,
                export_format="pdf",
                deleted_at=trashed_at,
            ),
            _export(owner, lineage_id=other_lineage, export_format="qti"),
            _export(other_owner, lineage_id=lineage, export_format="qti"),
        ]:
            await repo.create(file=row)

        active = await repo.list_exam_files(
            user_id=owner, document_lineage_id=lineage, include_deleted=False
        )
        assert [row.export_format for row in active] == [None, "qti"]

        with_trash = await repo.list_exam_files(
            user_id=owner, document_lineage_id=lineage, include_deleted=True
        )
        assert [row.export_format for row in with_trash] == [None, "pdf", "qti"]
        assert {row.user_id for row in with_trash} == {owner}
        assert {row.document_lineage_id for row in with_trash} == {lineage}
        await session.rollback()


async def test_delete_purges_the_named_row_and_the_exam_history_only(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = PostgreSQLUserVaultFileRepository(session)
        owner = await _owner(session)
        lineage = uuid4()
        exam = _exam(owner, lineage_id=lineage)
        export = _export(owner, lineage_id=lineage, export_format="qti")
        await repo.create(file=exam)
        await repo.create(file=export)
        await repo.put_history(user_id=owner, document_lineage_id=lineage, content=b"history")

        await repo.delete(file_id=exam.id)

        assert await repo.get_by_id(file_id=exam.id) is None
        assert await repo.get_history(user_id=owner, document_lineage_id=lineage) is None
        # The saved export row survives until its own payload is gone: the purge
        # producer deletes the payloads of the expired group before the rows.
        assert await repo.get_by_id(file_id=export.id) is not None

        await repo.put_history(user_id=owner, document_lineage_id=lineage, content=b"history")
        await repo.delete(file_id=export.id)

        assert await repo.get_by_id(file_id=export.id) is None
        assert await repo.get_history(user_id=owner, document_lineage_id=lineage) == b"history"
        await session.rollback()


async def test_update_moves_the_trash_flag_and_an_overwrite_keeps_it(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = PostgreSQLUserVaultFileRepository(session)
        owner = await _owner(session)
        lineage = uuid4()
        export = _export(owner, lineage_id=lineage, export_format="qti")
        created = await repo.create(file=export)
        assert created.trashed_with_exam is False

        trashed = created.model_copy(update={"deleted_at": _NOW, "trashed_with_exam": True})
        updated = await repo.update(file=trashed)
        assert updated.deleted_at == _NOW
        assert updated.trashed_with_exam is True

        # An overwrite carries the payload, not the lifecycle: a caller that hands over
        # a stale flag must not clear the row's trash provenance.
        overwritten = await repo.overwrite(
            file=updated.model_copy(update={"bytes": 84, "trashed_with_exam": False})
        )
        assert overwritten.bytes == 84
        stored = await repo.get_by_id(file_id=export.id)
        assert stored is not None
        assert stored.deleted_at == _NOW
        assert stored.trashed_with_exam is True
        await session.rollback()
