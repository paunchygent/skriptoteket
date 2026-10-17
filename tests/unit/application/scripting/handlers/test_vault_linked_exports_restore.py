"""Restore, quota and retention behavior for linked saved exam exports."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.vault import RestoreVaultFileCommand
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.scripting.handlers.vault_linked_exports_lifecycle_test_support import (
    _exam_document_row,
    _JournalUsageRepo,
    _LifecycleJournalRepo,
    _PurgedWhileLockingRepo,
    _restore_handler,
    _saved_export,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_restore_exam_returns_only_the_exports_trashed_with_it(now: datetime) -> None:
    actor = make_user(role=Role.USER, user_id=uuid4())
    journal: list[str] = []
    repo = _LifecycleJournalRepo(journal)
    usage = _JournalUsageRepo(journal)
    lineage_id = uuid4()
    exam = _exam_document_row(
        user_id=actor.id, lineage_id=lineage_id, now=now, deleted_at=now, trashed_with_exam=True
    )
    came_along = _saved_export(
        user_id=actor.id,
        lineage_id=lineage_id,
        now=now,
        export_format="qti",
        file_bytes=10,
        deleted_at=now,
        trashed_with_exam=True,
    )
    # Trashed on its own at the same moment: the clock cannot tell the two apart, only
    # the flag can, so this export must stay in the trash when the exam returns.
    trashed_on_its_own = _saved_export(
        user_id=actor.id,
        lineage_id=lineage_id,
        now=now,
        export_format="pdf",
        file_bytes=20,
        deleted_at=now,
        trashed_with_exam=False,
    )
    for file in (exam, came_along, trashed_on_its_own):
        repo.files[file.id] = file
    usage.seed_total(user_id=actor.id, bytes_total=0, now=now)

    result = await _restore_handler(repo=repo, usage=usage, now=now).handle(
        actor=actor, command=RestoreVaultFileCommand(file_id=exam.id)
    )

    assert result.file.deleted_at is None
    assert repo.files[exam.id].deleted_at is None
    assert repo.files[exam.id].trashed_with_exam is False
    assert repo.files[came_along.id].deleted_at is None
    assert repo.files[came_along.id].trashed_with_exam is False
    assert repo.files[trashed_on_its_own.id].deleted_at == now
    assert repo.files[trashed_on_its_own.id].trashed_with_exam is False
    assert usage.total(user_id=actor.id) == 110
    assert journal == [
        "lineage_lock",
        "usage_lock",
        f"update:{exam.id}",
        f"update:{came_along.id}",
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_restore_saved_export_returns_the_owning_exam_it_was_trashed_with(
    now: datetime,
) -> None:
    actor = make_user(role=Role.USER, user_id=uuid4())
    journal: list[str] = []
    repo = _LifecycleJournalRepo(journal)
    usage = _JournalUsageRepo(journal)
    lineage_id = uuid4()
    exam = _exam_document_row(
        user_id=actor.id, lineage_id=lineage_id, now=now, deleted_at=now, trashed_with_exam=True
    )
    came_along = _saved_export(
        user_id=actor.id,
        lineage_id=lineage_id,
        now=now,
        export_format="qti",
        file_bytes=10,
        deleted_at=now,
        trashed_with_exam=True,
    )
    trashed_on_its_own = _saved_export(
        user_id=actor.id,
        lineage_id=lineage_id,
        now=now,
        export_format="pdf",
        file_bytes=20,
        deleted_at=now - timedelta(days=1),
    )
    for file in (exam, came_along, trashed_on_its_own):
        repo.files[file.id] = file
    usage.seed_total(user_id=actor.id, bytes_total=0, now=now)

    result = await _restore_handler(repo=repo, usage=usage, now=now).handle(
        actor=actor, command=RestoreVaultFileCommand(file_id=trashed_on_its_own.id)
    )

    # The export cannot be active under a trashed exam, so the exam comes back with it,
    # together with the exports that were trashed with the exam.
    assert result.file.id == trashed_on_its_own.id
    assert repo.files[trashed_on_its_own.id].deleted_at is None
    assert repo.files[exam.id].deleted_at is None
    assert repo.files[exam.id].trashed_with_exam is False
    assert repo.files[came_along.id].deleted_at is None
    assert repo.files[came_along.id].trashed_with_exam is False
    assert usage.total(user_id=actor.id) == 130


@pytest.mark.unit
@pytest.mark.asyncio
async def test_restore_saved_export_of_an_active_exam_returns_only_that_export(
    now: datetime,
) -> None:
    actor = make_user(role=Role.USER, user_id=uuid4())
    journal: list[str] = []
    repo = _LifecycleJournalRepo(journal)
    usage = _JournalUsageRepo(journal)
    lineage_id = uuid4()
    exam = _exam_document_row(user_id=actor.id, lineage_id=lineage_id, now=now)
    qti = _saved_export(
        user_id=actor.id,
        lineage_id=lineage_id,
        now=now,
        export_format="qti",
        file_bytes=10,
        deleted_at=now - timedelta(days=1),
    )
    for file in (exam, qti):
        repo.files[file.id] = file
    usage.seed_total(user_id=actor.id, bytes_total=100, now=now)

    result = await _restore_handler(repo=repo, usage=usage, now=now).handle(
        actor=actor, command=RestoreVaultFileCommand(file_id=qti.id)
    )

    assert result.file.deleted_at is None
    assert repo.files[qti.id].deleted_at is None
    assert repo.files[exam.id].deleted_at is None
    assert usage.total(user_id=actor.id) == 110
    assert journal == ["lineage_lock", "usage_lock", f"update:{qti.id}"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_restore_exam_over_quota_leaves_every_row_in_the_trash(now: datetime) -> None:
    actor = make_user(role=Role.USER, user_id=uuid4())
    journal: list[str] = []
    repo = _LifecycleJournalRepo(journal)
    usage = _JournalUsageRepo(journal)
    lineage_id = uuid4()
    exam = _exam_document_row(
        user_id=actor.id, lineage_id=lineage_id, now=now, deleted_at=now, trashed_with_exam=True
    )
    qti = _saved_export(
        user_id=actor.id,
        lineage_id=lineage_id,
        now=now,
        export_format="qti",
        file_bytes=10,
        deleted_at=now,
        trashed_with_exam=True,
    )
    for file in (exam, qti):
        repo.files[file.id] = file
    # The exam alone would fit; the exam with its saved export does not.
    settings = Settings(VAULT_MAX_TOTAL_BYTES=105)

    with pytest.raises(DomainError) as error:
        await _restore_handler(repo=repo, usage=usage, now=now, settings=settings).handle(
            actor=actor, command=RestoreVaultFileCommand(file_id=exam.id)
        )

    assert error.value.code is ErrorCode.VALIDATION_ERROR
    assert error.value.details == {
        "bytes_total": 0,
        "attempted_bytes": 110,
        "max_total_bytes": 105,
    }
    assert repo.files[exam.id].deleted_at == now
    assert repo.files[exam.id].trashed_with_exam is True
    assert repo.files[qti.id].deleted_at == now
    assert usage.total(user_id=actor.id) == 0
    assert journal == ["lineage_lock", "usage_lock"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_restore_exam_ignores_an_expired_export_trashed_on_its_own(now: datetime) -> None:
    actor = make_user(role=Role.USER, user_id=uuid4())
    journal: list[str] = []
    repo = _LifecycleJournalRepo(journal)
    usage = _JournalUsageRepo(journal)
    lineage_id = uuid4()
    exam = _exam_document_row(
        user_id=actor.id,
        lineage_id=lineage_id,
        now=now,
        deleted_at=now - timedelta(days=1),
        trashed_with_exam=True,
    )
    # Trashed on its own long ago, so it is past retention and not part of the exam's
    # restore: the cleanup purges it, the exam still comes back.
    expired_own_trash = _saved_export(
        user_id=actor.id,
        lineage_id=lineage_id,
        now=now,
        export_format="pdf",
        file_bytes=20,
        deleted_at=now - timedelta(days=40),
    )
    for file in (exam, expired_own_trash):
        repo.files[file.id] = file

    result = await _restore_handler(repo=repo, usage=usage, now=now).handle(
        actor=actor, command=RestoreVaultFileCommand(file_id=exam.id)
    )

    assert result.file.deleted_at is None
    assert repo.files[expired_own_trash.id].deleted_at == now - timedelta(days=40)
    assert usage.total(user_id=actor.id) == 100


@pytest.mark.unit
@pytest.mark.asyncio
async def test_restore_exam_rejects_a_saved_export_that_passed_retention(now: datetime) -> None:
    actor = make_user(role=Role.USER, user_id=uuid4())
    journal: list[str] = []
    repo = _LifecycleJournalRepo(journal)
    usage = _JournalUsageRepo(journal)
    lineage_id = uuid4()
    exam = _exam_document_row(
        user_id=actor.id,
        lineage_id=lineage_id,
        now=now,
        deleted_at=now - timedelta(days=1),
        trashed_with_exam=True,
    )
    expired_pdf = _saved_export(
        user_id=actor.id,
        lineage_id=lineage_id,
        now=now,
        export_format="pdf",
        file_bytes=20,
        deleted_at=now - timedelta(days=40),
        trashed_with_exam=True,
    )
    for file in (exam, expired_pdf):
        repo.files[file.id] = file

    with pytest.raises(DomainError) as error:
        await _restore_handler(repo=repo, usage=usage, now=now).handle(
            actor=actor, command=RestoreVaultFileCommand(file_id=exam.id)
        )

    assert error.value.code is ErrorCode.VALIDATION_ERROR
    assert (error.value.details or {}).get("expired_file_ids") == [str(expired_pdf.id)]
    assert repo.files[exam.id].deleted_at is not None
    assert usage.total(user_id=actor.id) == 0
    assert journal == ["lineage_lock"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_restore_of_a_row_purged_while_waiting_for_the_lock_is_not_found(
    now: datetime,
) -> None:
    actor = make_user(role=Role.USER, user_id=uuid4())
    journal: list[str] = []
    lineage_id = uuid4()
    exam = _exam_document_row(
        user_id=actor.id, lineage_id=lineage_id, now=now, deleted_at=now, trashed_with_exam=True
    )
    repo = _PurgedWhileLockingRepo(journal, purged_file_id=exam.id)
    repo.files[exam.id] = exam
    usage = _JournalUsageRepo(journal)

    with pytest.raises(DomainError) as error:
        await _restore_handler(repo=repo, usage=usage, now=now).handle(
            actor=actor, command=RestoreVaultFileCommand(file_id=exam.id)
        )

    assert error.value.code is ErrorCode.NOT_FOUND
    assert usage.total(user_id=actor.id) == 0
    assert journal == ["lineage_lock"]
