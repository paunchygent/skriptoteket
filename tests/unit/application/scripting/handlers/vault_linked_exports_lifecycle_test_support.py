"""Shared repositories, row builders and handlers for linked-export lifecycle tests."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from skriptoteket.application.scripting.handlers.delete_vault_file import DeleteVaultFileHandler
from skriptoteket.application.scripting.handlers.list_vault_files import ListVaultFilesHandler
from skriptoteket.application.scripting.handlers.restore_vault_file import RestoreVaultFileHandler
from skriptoteket.config import Settings
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind, VaultUsage
from tests.unit.application.curated_apps.handlers.vault_file_repository_test_support import (
    InMemoryVaultFileRepository,
)
from tests.unit.application.scripting.handlers.vault_test_support import (
    FakeClock,
    FakeCuratedApps,
    FakeRuns,
    FakeTools,
    FakeUow,
    FakeVaultStorage,
    FakeVaultUsageRepo,
)


class _LifecycleJournalRepo(InMemoryVaultFileRepository):
    """The shared in-memory repository, recording the order of the lifecycle calls."""

    def __init__(self, journal: list[str]) -> None:
        super().__init__()
        self._journal = journal

    async def lock_document_lineage(self, *, user_id: UUID, document_lineage_id: UUID) -> None:
        self._journal.append("lineage_lock")
        await super().lock_document_lineage(
            user_id=user_id, document_lineage_id=document_lineage_id
        )

    async def update(self, *, file: VaultFile) -> VaultFile:
        self._journal.append(f"update:{file.id}")
        return await super().update(file=file)


class _PurgedWhileLockingRepo(_LifecycleJournalRepo):
    """The shared fake, purging one row while a request waits for the lineage lock."""

    def __init__(self, journal: list[str], *, purged_file_id: UUID) -> None:
        super().__init__(journal)
        self._purged_file_id = purged_file_id

    async def lock_document_lineage(self, *, user_id: UUID, document_lineage_id: UUID) -> None:
        self.files.pop(self._purged_file_id, None)
        await super().lock_document_lineage(
            user_id=user_id, document_lineage_id=document_lineage_id
        )


class _JournalUsageRepo(FakeVaultUsageRepo):
    """The shared usage fake, recording when the byte accounting takes its lock."""

    def __init__(self, journal: list[str]) -> None:
        super().__init__()
        self._journal = journal

    def seed_total(self, *, user_id: UUID, bytes_total: int, now: datetime) -> None:
        self._usage[user_id] = VaultUsage(user_id=user_id, bytes_total=bytes_total, updated_at=now)

    def total(self, *, user_id: UUID) -> int:
        usage = self._usage.get(user_id)
        return usage.bytes_total if usage else 0

    async def get_for_update(self, *, user_id: UUID, now: datetime) -> VaultUsage:
        self._journal.append("usage_lock")
        return await super().get_for_update(user_id=user_id, now=now)


def _exam_document_row(
    *, user_id: UUID, lineage_id: UUID, now: datetime, **updates: object
) -> VaultFile:
    return VaultFile(
        id=uuid4(),
        user_id=user_id,
        name="Prov.provdokument.zip",
        bytes=100,
        source_kind=VaultFileSourceKind.APP_EXPORT,
        source_artifact_id=f"exam_workspace:{lineage_id}",
        document_lineage_id=lineage_id,
        document_version=1,
        created_at=now,
    ).model_copy(update=updates)


def _saved_export(
    *,
    user_id: UUID,
    lineage_id: UUID,
    now: datetime,
    export_format: str,
    file_bytes: int,
    **updates: object,
) -> VaultFile:
    return VaultFile(
        id=uuid4(),
        user_id=user_id,
        name=f"Prov-{export_format}",
        bytes=file_bytes,
        source_kind=VaultFileSourceKind.APP_EXPORT,
        source_artifact_id=f"exam_workspace:{lineage_id}:{export_format}",
        document_lineage_id=lineage_id,
        document_version=1,
        export_format=export_format,
        created_at=now,
    ).model_copy(update=updates)


def _plain_file(*, user_id: UUID, now: datetime, **updates: object) -> VaultFile:
    return VaultFile(
        id=uuid4(),
        user_id=user_id,
        name="Vanlig.pdf",
        bytes=5,
        source_kind=VaultFileSourceKind.RUN_ARTIFACT,
        source_run_id=None,
        source_artifact_id=None,
        created_at=now,
    ).model_copy(update=updates)


def _delete_handler(
    *, repo: InMemoryVaultFileRepository, usage: FakeVaultUsageRepo, now: datetime
) -> DeleteVaultFileHandler:
    return DeleteVaultFileHandler(
        uow=FakeUow(), vault_files=repo, vault_usage=usage, clock=FakeClock(now)
    )


def _restore_handler(
    *,
    repo: InMemoryVaultFileRepository,
    usage: FakeVaultUsageRepo,
    now: datetime,
    settings: Settings | None = None,
) -> RestoreVaultFileHandler:
    return RestoreVaultFileHandler(
        uow=FakeUow(),
        vault_files=repo,
        vault_usage=usage,
        settings=settings or Settings(),
        clock=FakeClock(now),
    )


def _list_handler(
    *, repo: InMemoryVaultFileRepository, usage: FakeVaultUsageRepo, storage: FakeVaultStorage
) -> ListVaultFilesHandler:
    return ListVaultFilesHandler(
        uow=FakeUow(),
        runs=FakeRuns(),
        tools=FakeTools(),
        curated_apps=FakeCuratedApps(),
        vault_files=repo,
        vault_usage=usage,
        vault_storage=storage,
        settings=Settings(),
    )
