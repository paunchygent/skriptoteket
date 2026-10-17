"""Trash and listing behavior for an exam and its linked saved exports."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.vault import DeleteVaultFileCommand, ListVaultFilesQuery
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.vault import VaultListState
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.curated_apps.handlers.vault_file_repository_test_support import (
    InMemoryVaultFileRepository,
)
from tests.unit.application.scripting.handlers.vault_linked_exports_lifecycle_test_support import (
    _delete_handler,
    _exam_document_row,
    _JournalUsageRepo,
    _LifecycleJournalRepo,
    _list_handler,
    _plain_file,
    _PurgedWhileLockingRepo,
    _saved_export,
)
from tests.unit.application.scripting.handlers.vault_test_support import (
    FakeVaultStorage,
    FakeVaultUsageRepo,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_exam_trashes_its_saved_exports_and_releases_their_bytes_once(
    now: datetime,
) -> None:
    actor = make_user(role=Role.USER, user_id=uuid4())
    journal: list[str] = []
    repo = _LifecycleJournalRepo(journal)
    usage = _JournalUsageRepo(journal)
    lineage_id = uuid4()
    exam = _exam_document_row(user_id=actor.id, lineage_id=lineage_id, now=now)
    qti = _saved_export(
        user_id=actor.id, lineage_id=lineage_id, now=now, export_format="qti", file_bytes=10
    )
    already_trashed_pdf = _saved_export(
        user_id=actor.id,
        lineage_id=lineage_id,
        now=now,
        export_format="pdf",
        file_bytes=20,
        deleted_at=now - timedelta(days=2),
    )
    for file in (exam, qti, already_trashed_pdf):
        repo.files[file.id] = file
    # The trashed export released its bytes when it moved, so only 100 + 10 are counted.
    usage.seed_total(user_id=actor.id, bytes_total=110, now=now)

    result = await _delete_handler(repo=repo, usage=usage, now=now).handle(
        actor=actor, command=DeleteVaultFileCommand(file_id=exam.id)
    )

    assert result.file.deleted_at == now
    assert repo.files[exam.id].deleted_at == now
    assert repo.files[qti.id].deleted_at == now
    # The exam's own trash marks the rows that came with it; an export the user trashed
    # earlier on its own is not marked and keeps its own timestamp.
    assert repo.files[exam.id].trashed_with_exam is True
    assert repo.files[qti.id].trashed_with_exam is True
    assert repo.files[already_trashed_pdf.id].deleted_at == now - timedelta(days=2)
    assert repo.files[already_trashed_pdf.id].trashed_with_exam is False
    assert usage.total(user_id=actor.id) == 0
    assert journal == [
        "lineage_lock",
        "usage_lock",
        f"update:{exam.id}",
        f"update:{qti.id}",
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_saved_export_moves_only_that_export_to_trash(now: datetime) -> None:
    actor = make_user(role=Role.USER, user_id=uuid4())
    journal: list[str] = []
    repo = _LifecycleJournalRepo(journal)
    usage = _JournalUsageRepo(journal)
    lineage_id = uuid4()
    exam = _exam_document_row(user_id=actor.id, lineage_id=lineage_id, now=now)
    qti = _saved_export(
        user_id=actor.id, lineage_id=lineage_id, now=now, export_format="qti", file_bytes=10
    )
    for file in (exam, qti):
        repo.files[file.id] = file
    usage.seed_total(user_id=actor.id, bytes_total=110, now=now)

    result = await _delete_handler(repo=repo, usage=usage, now=now).handle(
        actor=actor, command=DeleteVaultFileCommand(file_id=qti.id)
    )

    assert result.file.deleted_at == now
    assert repo.files[qti.id].deleted_at == now
    assert repo.files[qti.id].trashed_with_exam is False
    assert repo.files[exam.id].deleted_at is None
    assert usage.total(user_id=actor.id) == 100
    assert journal == ["lineage_lock", "usage_lock", f"update:{qti.id}"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_of_a_row_purged_while_waiting_for_the_lock_is_not_found(
    now: datetime,
) -> None:
    actor = make_user(role=Role.USER, user_id=uuid4())
    journal: list[str] = []
    lineage_id = uuid4()
    exam = _exam_document_row(user_id=actor.id, lineage_id=lineage_id, now=now)
    repo = _PurgedWhileLockingRepo(journal, purged_file_id=exam.id)
    repo.files[exam.id] = exam
    usage = _JournalUsageRepo(journal)
    usage.seed_total(user_id=actor.id, bytes_total=100, now=now)

    with pytest.raises(DomainError) as error:
        await _delete_handler(repo=repo, usage=usage, now=now).handle(
            actor=actor, command=DeleteVaultFileCommand(file_id=exam.id)
        )

    # The pre-lock row is never replayed as the answer, and no byte accounting runs
    # against a file that a concurrent purge removed.
    assert error.value.code is ErrorCode.NOT_FOUND
    assert usage.total(user_id=actor.id) == 100
    assert journal == ["lineage_lock"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_nests_saved_exports_under_their_exam_in_both_states(now: datetime) -> None:
    actor = make_user(role=Role.USER, user_id=uuid4())
    repo = InMemoryVaultFileRepository()
    usage = FakeVaultUsageRepo()
    storage = FakeVaultStorage()
    active_lineage = uuid4()
    trashed_lineage = uuid4()
    active_exam = _exam_document_row(
        user_id=actor.id, lineage_id=active_lineage, now=now - timedelta(hours=4)
    )
    active_pdf = _saved_export(
        user_id=actor.id,
        lineage_id=active_lineage,
        now=now - timedelta(hours=4),
        export_format="pdf",
        file_bytes=20,
    )
    active_qti = _saved_export(
        user_id=actor.id,
        lineage_id=active_lineage,
        now=now - timedelta(hours=4),
        export_format="qti",
        file_bytes=10,
    )
    # A saved export that was trashed on its own stays out of the active exam's list and
    # is never a standalone row in either state.
    lone_trashed_export = _saved_export(
        user_id=actor.id,
        lineage_id=active_lineage,
        now=now - timedelta(hours=3),
        export_format="docx",
        file_bytes=30,
        deleted_at=now - timedelta(hours=2),
    )
    plain = _plain_file(user_id=actor.id, now=now - timedelta(hours=1))
    trashed_exam = _exam_document_row(
        user_id=actor.id,
        lineage_id=trashed_lineage,
        now=now - timedelta(hours=5),
        deleted_at=now - timedelta(hours=2),
        trashed_with_exam=True,
    )
    trashed_qti = _saved_export(
        user_id=actor.id,
        lineage_id=trashed_lineage,
        now=now - timedelta(hours=5),
        export_format="qti",
        file_bytes=10,
        deleted_at=now - timedelta(hours=2),
        trashed_with_exam=True,
    )
    for file in (
        active_exam,
        active_pdf,
        active_qti,
        lone_trashed_export,
        plain,
        trashed_exam,
        trashed_qti,
    ):
        repo.files[file.id] = file
    handler = _list_handler(repo=repo, usage=usage, storage=storage)

    active_page = await handler.handle(
        actor=actor, query=ListVaultFilesQuery(state=VaultListState.ACTIVE)
    )
    assert [info.id for info in active_page.files] == [plain.id, active_exam.id]
    assert [export.id for export in active_page.files[1].exports] == [active_pdf.id, active_qti.id]
    assert active_page.files[0].exports == []

    # Export rows never consume a page slot: the page holds whole exams only.
    active_first_page = await handler.handle(
        actor=actor, query=ListVaultFilesQuery(state=VaultListState.ACTIVE, limit=1)
    )
    assert [info.id for info in active_first_page.files] == [plain.id]
    active_second_page = await handler.handle(
        actor=actor, query=ListVaultFilesQuery(state=VaultListState.ACTIVE, limit=1, cursor=1)
    )
    assert [info.id for info in active_second_page.files] == [active_exam.id]

    trash_page = await handler.handle(
        actor=actor, query=ListVaultFilesQuery(state=VaultListState.TRASH)
    )
    assert [info.id for info in trash_page.files] == [trashed_exam.id]
    assert [export.id for export in trash_page.files[0].exports] == [trashed_qti.id]
