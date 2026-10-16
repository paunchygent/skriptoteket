from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.handlers.delete_vault_file import DeleteVaultFileHandler
from skriptoteket.application.scripting.handlers.list_vault_files import ListVaultFilesHandler
from skriptoteket.application.scripting.handlers.restore_vault_file import RestoreVaultFileHandler
from skriptoteket.application.scripting.handlers.save_vault_file import SaveVaultFileHandler
from skriptoteket.application.scripting.vault import (
    DeleteVaultFileCommand,
    ListVaultFilesQuery,
    RestoreVaultFileCommand,
    SaveVaultFileCommand,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.artifacts import (
    ArtifactsManifest,
    StoredArtifact,
)
from skriptoteket.domain.scripting.models import RunContext
from skriptoteket.domain.scripting.vault import (
    VaultFile,
    VaultFileSourceKind,
    VaultUsage,
)
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.scripting.handlers.sandbox_test_support import make_tool_run
from tests.unit.application.scripting.handlers.vault_test_support import (
    FakeArtifactManager,
    FakeClock,
    FakeCuratedApps,
    FakeIdGenerator,
    FakeRuns,
    FakeTools,
    FakeUow,
    FakeVaultFileRepo,
    FakeVaultStorage,
    FakeVaultUsageRepo,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_vault_file_stores_bytes_and_updates_usage(now: datetime) -> None:
    actor = make_user(role=Role.USER, user_id=uuid4())
    tool_id = uuid4()
    version_id = uuid4()
    run = make_tool_run(
        tool_id=tool_id,
        version_id=version_id,
        requested_by_user_id=actor.id,
        now=now,
        context=RunContext.PRODUCTION,
    ).model_copy(
        update={
            "artifacts_manifest": ArtifactsManifest(
                artifacts=[StoredArtifact(artifact_id="report", path="output/report.pdf", bytes=4)]
            ).model_dump()
        }
    )

    runs = FakeRuns(runs_by_id={run.id: run})

    vault_files = FakeVaultFileRepo()
    vault_usage = FakeVaultUsageRepo()
    vault_storage = FakeVaultStorage()
    settings = Settings()
    clock = FakeClock(now)
    id_generator = FakeIdGenerator(uuid4())
    artifacts = FakeArtifactManager(content=b"data")

    handler = SaveVaultFileHandler(
        uow=FakeUow(),
        runs=runs,
        artifacts=artifacts,
        vault_files=vault_files,
        vault_usage=vault_usage,
        vault_storage=vault_storage,
        settings=settings,
        clock=clock,
        id_generator=id_generator,
    )

    result = await handler.handle(
        actor=actor,
        command=SaveVaultFileCommand(
            source_kind=VaultFileSourceKind.RUN_ARTIFACT,
            run_id=run.id,
            artifact_id="report",
        ),
    )

    assert result.file.name == "report.pdf"
    stored = await vault_storage.read_file(user_id=actor.id, file_id=result.file.id)
    assert stored == b"data"
    usage = await vault_usage.get(user_id=actor.id)
    assert usage is not None
    assert usage.bytes_total == 4


@pytest.mark.unit
@pytest.mark.asyncio
async def test_restore_vault_file_rejects_expired(now: datetime) -> None:
    actor = make_user(role=Role.USER, user_id=uuid4())
    file_id = uuid4()
    expired_at = now - timedelta(days=31)

    vault_files = FakeVaultFileRepo()
    vault_files._files[file_id] = VaultFile(
        id=file_id,
        user_id=actor.id,
        name="expired.txt",
        bytes=12,
        source_kind=VaultFileSourceKind.RUN_ARTIFACT,
        source_run_id=None,
        source_artifact_id=None,
        created_at=now,
        deleted_at=expired_at,
    )

    handler = RestoreVaultFileHandler(
        uow=FakeUow(),
        vault_files=vault_files,
        vault_usage=FakeVaultUsageRepo(),
        settings=Settings(),
        clock=FakeClock(now),
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=RestoreVaultFileCommand(file_id=file_id),
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_vault_file_marks_deleted_and_updates_usage(now: datetime) -> None:
    actor = make_user(role=Role.USER, user_id=uuid4())
    file_id = uuid4()
    vault_files = FakeVaultFileRepo()
    vault_files._files[file_id] = VaultFile(
        id=file_id,
        user_id=actor.id,
        name="report.pdf",
        bytes=10,
        source_kind=VaultFileSourceKind.RUN_ARTIFACT,
        source_run_id=None,
        source_artifact_id=None,
        created_at=now,
        deleted_at=None,
    )

    vault_usage = FakeVaultUsageRepo()
    vault_usage._usage[actor.id] = VaultUsage(user_id=actor.id, bytes_total=10, updated_at=now)

    handler = DeleteVaultFileHandler(
        uow=FakeUow(),
        vault_files=vault_files,
        vault_usage=vault_usage,
        clock=FakeClock(now),
    )

    result = await handler.handle(
        actor=actor,
        command=DeleteVaultFileCommand(file_id=file_id),
    )

    assert result.file.deleted_at == now
    usage = await vault_usage.get(user_id=actor.id)
    assert usage is not None
    assert usage.bytes_total == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_restore_vault_file_restores_and_updates_usage(now: datetime) -> None:
    actor = make_user(role=Role.USER, user_id=uuid4())
    file_id = uuid4()
    deleted_at = now - timedelta(days=1)
    vault_files = FakeVaultFileRepo()
    vault_files._files[file_id] = VaultFile(
        id=file_id,
        user_id=actor.id,
        name="restore.txt",
        bytes=12,
        source_kind=VaultFileSourceKind.RUN_ARTIFACT,
        source_run_id=None,
        source_artifact_id=None,
        created_at=now,
        deleted_at=deleted_at,
    )
    vault_usage = FakeVaultUsageRepo()
    vault_usage._usage[actor.id] = VaultUsage(user_id=actor.id, bytes_total=0, updated_at=now)

    handler = RestoreVaultFileHandler(
        uow=FakeUow(),
        vault_files=vault_files,
        vault_usage=vault_usage,
        settings=Settings(VAULT_MAX_TOTAL_BYTES=100),
        clock=FakeClock(now),
    )

    result = await handler.handle(
        actor=actor,
        command=RestoreVaultFileCommand(file_id=file_id),
    )

    assert result.file.deleted_at is None
    usage = await vault_usage.get(user_id=actor.id)
    assert usage is not None
    assert usage.bytes_total == 12


@pytest.mark.unit
@pytest.mark.asyncio
async def test_restore_vault_file_rejects_quota(now: datetime) -> None:
    actor = make_user(role=Role.USER, user_id=uuid4())
    file_id = uuid4()
    vault_files = FakeVaultFileRepo()
    vault_files._files[file_id] = VaultFile(
        id=file_id,
        user_id=actor.id,
        name="over.txt",
        bytes=10,
        source_kind=VaultFileSourceKind.RUN_ARTIFACT,
        source_run_id=None,
        source_artifact_id=None,
        created_at=now,
        deleted_at=now - timedelta(days=1),
    )
    vault_usage = FakeVaultUsageRepo()
    vault_usage._usage[actor.id] = VaultUsage(user_id=actor.id, bytes_total=5, updated_at=now)

    handler = RestoreVaultFileHandler(
        uow=FakeUow(),
        vault_files=vault_files,
        vault_usage=vault_usage,
        settings=Settings(VAULT_MAX_TOTAL_BYTES=10),
        clock=FakeClock(now),
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=RestoreVaultFileCommand(file_id=file_id),
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_vault_file_rejects_invalid_manifest(now: datetime) -> None:
    actor = make_user(role=Role.USER, user_id=uuid4())
    tool_id = uuid4()
    version_id = uuid4()
    run = make_tool_run(
        tool_id=tool_id,
        version_id=version_id,
        requested_by_user_id=actor.id,
        now=now,
        context=RunContext.PRODUCTION,
    ).model_copy(
        update={"artifacts_manifest": {"artifacts": [{"path": "output/report.pdf", "bytes": 4}]}}
    )

    runs = FakeRuns(runs_by_id={run.id: run})

    handler = SaveVaultFileHandler(
        uow=FakeUow(),
        runs=runs,
        artifacts=FakeArtifactManager(content=b"data"),
        vault_files=FakeVaultFileRepo(),
        vault_usage=FakeVaultUsageRepo(),
        vault_storage=FakeVaultStorage(),
        settings=Settings(),
        clock=FakeClock(now),
        id_generator=FakeIdGenerator(uuid4()),
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=SaveVaultFileCommand(
                source_kind=VaultFileSourceKind.RUN_ARTIFACT,
                run_id=run.id,
                artifact_id="report",
            ),
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_vault_files_returns_usage_and_pagination(now: datetime) -> None:
    actor = make_user(role=Role.USER, user_id=uuid4())
    vault_files = FakeVaultFileRepo()
    file_id = uuid4()
    vault_files._files[file_id] = VaultFile(
        id=file_id,
        user_id=actor.id,
        name="alpha.txt",
        bytes=1,
        source_kind=VaultFileSourceKind.RUN_ARTIFACT,
        source_run_id=None,
        source_artifact_id=None,
        created_at=now - timedelta(days=1),
        deleted_at=None,
    )
    file_id = uuid4()
    vault_files._files[file_id] = VaultFile(
        id=file_id,
        user_id=actor.id,
        name="beta.txt",
        bytes=2,
        source_kind=VaultFileSourceKind.RUN_ARTIFACT,
        source_run_id=None,
        source_artifact_id=None,
        created_at=now,
        deleted_at=None,
    )
    file_id = uuid4()
    vault_files._files[file_id] = VaultFile(
        id=file_id,
        user_id=actor.id,
        name="gamma.txt",
        bytes=3,
        source_kind=VaultFileSourceKind.RUN_ARTIFACT,
        source_run_id=None,
        source_artifact_id=None,
        created_at=now - timedelta(days=2),
        deleted_at=None,
    )
    vault_usage = FakeVaultUsageRepo()
    vault_usage._usage[actor.id] = VaultUsage(user_id=actor.id, bytes_total=6, updated_at=now)

    runs = FakeRuns()
    tools = FakeTools()
    curated_apps = FakeCuratedApps()

    handler = ListVaultFilesHandler(
        uow=FakeUow(),
        runs=runs,
        tools=tools,
        curated_apps=curated_apps,
        vault_files=vault_files,
        vault_usage=vault_usage,
        vault_storage=FakeVaultStorage(),
        settings=Settings(VAULT_MAX_TOTAL_BYTES=10, VAULT_MAX_FILE_BYTES=5),
    )

    result = await handler.handle(
        actor=actor,
        query=ListVaultFilesQuery(limit=2),
    )

    assert len(result.files) == 2
    assert result.next_cursor == "2"
    assert result.usage.bytes_total == 6
    assert result.usage.max_total_bytes == 10
    assert result.usage.max_file_bytes == 5
