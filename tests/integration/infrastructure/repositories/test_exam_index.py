"""Saved-index lifecycle and atomic writes against real PostgreSQL, not mock ports."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.container import ExamWorkspaceContainerContent
from skriptoteket.domain.curated_apps.exam_workspace.exam_index import ExamIndexEntry
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_versions import (
    CURRENT_NATIVE_EXAM_DOCUMENT_VERSION,
    OLDEST_READABLE_NATIVE_EXAM_DOCUMENT_VERSION,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.repositories.exam_index_repository import (
    PostgreSQLExamIndexRepository,
)
from skriptoteket.infrastructure.repositories.user_vault_file_repository import (
    PostgreSQLUserVaultFileRepository,
)
from skriptoteket.infrastructure.repositories.user_vault_usage_repository import (
    PostgreSQLUserVaultUsageRepository,
)
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from tests.fixtures.payload_guard_fixtures import unpooled_payload_guard_engine
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.infrastructure.repositories.exam_workspace_test_support import create_owner
from tests.integration.infrastructure.repositories.test_exam_workspace_repositories import (
    _exam_file,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_conversion_support import choice

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]
_NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)


async def test_upsert_joins_live_filename_isolates_owner_and_tracks_trash_restore_delete(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    owner, stranger = await create_owner(session_factory), await create_owner(session_factory)
    lineage = uuid4()
    file = _exam_file(owner_id=owner.id, lineage_id=lineage, version=1, created_at=_NOW)
    other = _exam_file(owner_id=stranger.id, lineage_id=lineage, version=1, created_at=_NOW)
    entry = ExamIndexEntry(
        owner_user_id=owner.id,
        lineage_id=lineage,
        course_key="SVESVE01",
        title="Teacher title",
        saved_at=_NOW,
        head_vault_file_id=file.id,
        document_format_version=CURRENT_NATIVE_EXAM_DOCUMENT_VERSION,
    )
    async with session_factory() as session, SQLAlchemyUnitOfWork(session):
        vault = PostgreSQLUserVaultFileRepository(
            session, unpooled_payload_guard_engine(session.bind)
        )
        await vault.create(file=file)
        await vault.create(file=other)
        index = PostgreSQLExamIndexRepository(session)
        await index.upsert(entry=entry)
        await index.upsert(
            entry=entry.model_copy(
                update={
                    "title": "Changed title",
                    "course_key": "ENGENG05",
                    "saved_at": _NOW + timedelta(days=1),
                }
            )
        )
    async with session_factory() as session, SQLAlchemyUnitOfWork(session):
        index = PostgreSQLExamIndexRepository(session)
        exams = await index.list_for_owner(owner_user_id=owner.id)
        assert len(exams) == 1
        assert exams[0].title == "Changed title"
        assert exams[0].course_key == "ENGENG05"
        assert exams[0].head_vault_file_id == file.id
        assert await index.list_for_owner(owner_user_id=stranger.id) == []
        assert await index.get(owner_user_id=stranger.id, lineage_id=lineage) is None
        renamed_file = await PostgreSQLUserVaultFileRepository(
            session, unpooled_payload_guard_engine(session.bind)
        ).rename_active(user_id=owner.id, file_id=file.id, name="Renamed.provdokument.zip")
        assert renamed_file is not None
    async with session_factory() as session, SQLAlchemyUnitOfWork(session):
        index = PostgreSQLExamIndexRepository(session)
        renamed = await index.get(owner_user_id=owner.id, lineage_id=lineage)
        assert renamed is not None
        assert renamed.name == "Renamed.provdokument.zip"
        assert renamed.title == "Changed title"
        assert renamed.saved_at == _NOW + timedelta(days=1)
        await session.execute(
            text("UPDATE user_vault_files SET deleted_at=:now WHERE id=:id"),
            {"id": file.id, "now": _NOW},
        )
        assert await index.list_for_owner(owner_user_id=owner.id) == []
        assert await index.get(owner_user_id=owner.id, lineage_id=lineage) is None
        assert (
            await session.scalar(
                text("SELECT count(*) FROM exam_index WHERE owner_user_id=:id"), {"id": owner.id}
            )
            == 1
        )
        await session.execute(
            text("UPDATE user_vault_files SET deleted_at=NULL WHERE id=:id"), {"id": file.id}
        )
        restored = await index.get(owner_user_id=owner.id, lineage_id=lineage)
        assert restored == renamed
        await PostgreSQLUserVaultFileRepository(
            session, unpooled_payload_guard_engine(session.bind)
        ).delete(file_id=file.id)
        assert (
            await session.scalar(
                text("SELECT count(*) FROM exam_index WHERE owner_user_id=:id"), {"id": owner.id}
            )
            == 0
        )


async def test_join_does_not_expose_cross_owner_wrong_lineage_or_export_heads(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    owner, stranger = await create_owner(session_factory), await create_owner(session_factory)
    async with session_factory() as session, SQLAlchemyUnitOfWork(session):
        vault, index = (
            PostgreSQLUserVaultFileRepository(session, unpooled_payload_guard_engine(session.bind)),
            PostgreSQLExamIndexRepository(session),
        )
        for wrong in ("owner", "lineage", "export"):
            lineage = uuid4()
            file = _exam_file(
                owner_id=stranger.id if wrong == "owner" else owner.id,
                lineage_id=uuid4() if wrong == "lineage" else lineage,
                version=1,
                created_at=_NOW,
                export_format="qti" if wrong == "export" else None,
            )
            await vault.create(file=file)
            await index.upsert(
                entry=ExamIndexEntry(
                    owner_user_id=owner.id,
                    lineage_id=lineage,
                    course_key=None,
                    title=wrong,
                    saved_at=_NOW,
                    head_vault_file_id=file.id,
                    document_format_version=CURRENT_NATIVE_EXAM_DOCUMENT_VERSION,
                )
            )
        assert await index.list_for_owner(owner_user_id=owner.id) == []


async def test_failed_outer_save_transaction_restores_index_vault_and_file_bytes_together(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    actor = await create_owner(session_factory)
    codec, storage = ExamWorkspaceContainerCodec(), LocalVaultStorage(vault_root=tmp_path)
    document = NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Committed title",
        items=(choice("body:0001", "Question"),),
        origin=NativeExamDocumentOrigin(kind="created"),
    )
    original = codec.build(content=ExamWorkspaceContainerContent(document=document))
    async with session_factory() as session:
        store = ExamWorkspaceDocumentStore(
            vault_files=PostgreSQLUserVaultFileRepository(
                session, unpooled_payload_guard_engine(session.bind)
            ),
            vault_usage=PostgreSQLUserVaultUsageRepository(session),
            vault_storage=storage,
            index=PostgreSQLExamIndexRepository(session),
            codec=codec,
            uow=SQLAlchemyUnitOfWork(session),
            clock=FixedClock(_NOW),
            settings=Settings.model_construct(
                VAULT_MAX_FILE_BYTES=5_000_000, VAULT_MAX_TOTAL_BYTES=50_000_000
            ),
        )
        file = await store.save(
            actor=actor,
            file_id=uuid4(),
            name="Exam.provdokument.zip",
            content=original,
            lineage_id=document.document_id,
            version=1,
        )
        with pytest.raises(RuntimeError, match="abort outer operation"):
            async with store.transaction(user_id=actor.id, lineage_id=document.document_id):
                await store.save(
                    actor=actor,
                    file_id=uuid4(),
                    name=file.name,
                    lineage_id=document.document_id,
                    version=2,
                    expected_revision=1,
                    preserve_editor_position=True,
                    content=codec.build(
                        content=ExamWorkspaceContainerContent(
                            document=document.model_copy(
                                update={
                                    "revision": 2,
                                    "title": "Uncommitted title",
                                }
                            )
                        )
                    ),
                )
                raise RuntimeError("abort outer operation")
    async with session_factory() as session:
        saved = await PostgreSQLExamIndexRepository(session).get(
            owner_user_id=actor.id,
            lineage_id=document.document_id,
        )
        assert saved is not None
        assert saved.title == "Committed title"
        assert saved.version == 1
        assert saved.head_vault_file_id == file.id
        assert saved.saved_at == _NOW
        assert await storage.read_file(user_id=actor.id, file_id=file.id) == original


async def test_readable_and_unreadable_listings_split_by_format_version(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    owner = await create_owner(session_factory)
    readable_lineage, older_lineage, zero_lineage, trashed_lineage = (
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
    )
    readable_file = _exam_file(
        owner_id=owner.id, lineage_id=readable_lineage, version=1, created_at=_NOW
    )
    older_file = _exam_file(owner_id=owner.id, lineage_id=older_lineage, version=1, created_at=_NOW)
    zero_file = _exam_file(owner_id=owner.id, lineage_id=zero_lineage, version=1, created_at=_NOW)
    trashed_file = _exam_file(
        owner_id=owner.id,
        lineage_id=trashed_lineage,
        version=1,
        created_at=_NOW,
        deleted_at=_NOW,
    )
    old_version = OLDEST_READABLE_NATIVE_EXAM_DOCUMENT_VERSION - 1
    assert old_version < OLDEST_READABLE_NATIVE_EXAM_DOCUMENT_VERSION
    entries = [
        ExamIndexEntry(
            owner_user_id=owner.id,
            lineage_id=readable_lineage,
            course_key=None,
            title="Readable",
            saved_at=_NOW,
            head_vault_file_id=readable_file.id,
            document_format_version=CURRENT_NATIVE_EXAM_DOCUMENT_VERSION,
        ),
        ExamIndexEntry(
            owner_user_id=owner.id,
            lineage_id=older_lineage,
            course_key=None,
            title="Older",
            saved_at=_NOW + timedelta(days=1),
            head_vault_file_id=older_file.id,
            document_format_version=old_version,
        ),
        ExamIndexEntry(
            owner_user_id=owner.id,
            lineage_id=zero_lineage,
            course_key=None,
            title="Zero",
            saved_at=_NOW - timedelta(days=1),
            head_vault_file_id=zero_file.id,
            document_format_version=0,
        ),
        ExamIndexEntry(
            owner_user_id=owner.id,
            lineage_id=trashed_lineage,
            course_key=None,
            title="Trashed",
            saved_at=_NOW + timedelta(days=2),
            head_vault_file_id=trashed_file.id,
            document_format_version=old_version,
        ),
    ]
    async with session_factory() as session, SQLAlchemyUnitOfWork(session):
        vault = PostgreSQLUserVaultFileRepository(
            session, unpooled_payload_guard_engine(session.bind)
        )
        for file in (readable_file, older_file, zero_file, trashed_file):
            await vault.create(file=file)
        index = PostgreSQLExamIndexRepository(session)
        for entry in entries:
            await index.upsert(entry=entry)
    async with session_factory() as session:
        index = PostgreSQLExamIndexRepository(session)
        readable = await index.list_for_owner(owner_user_id=owner.id)
        assert [exam.title for exam in readable] == ["Readable"]
        unreadable = await index.list_unreadable_for_owner(owner_user_id=owner.id)
        assert [exam.title for exam in unreadable] == ["Older", "Zero"]
        assert await index.get(owner_user_id=owner.id, lineage_id=older_lineage) is not None
        assert await index.get(owner_user_id=owner.id, lineage_id=zero_lineage) is not None
