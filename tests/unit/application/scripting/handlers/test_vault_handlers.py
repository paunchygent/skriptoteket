from __future__ import annotations

from datetime import datetime, timedelta
from types import TracebackType
from typing import Iterable
from uuid import UUID, uuid4

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
from skriptoteket.domain.catalog.models import Tool
from skriptoteket.domain.curated_apps.models import CuratedAppDefinition
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.artifacts import (
    ArtifactsManifest,
    RunnerArtifact,
    StoredArtifact,
)
from skriptoteket.domain.scripting.models import RunContext, ToolRun
from skriptoteket.domain.scripting.vault import (
    VaultFile,
    VaultFileSourceKind,
    VaultListSort,
    VaultListState,
    VaultUsage,
)
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.runner import ArtifactManagerProtocol
from skriptoteket.protocols.scripting import RecentRunRow, ToolRunRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.scripting.handlers.sandbox_test_support import make_tool_run


class FakeUow(UnitOfWorkProtocol):
    async def __aenter__(self) -> UnitOfWorkProtocol:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None


class FakeClock(ClockProtocol):
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class FakeIdGenerator(IdGeneratorProtocol):
    def __init__(self, value: UUID) -> None:
        self._value = value

    def new_uuid(self) -> UUID:
        return self._value


class FakeArtifactManager(ArtifactManagerProtocol):
    def __init__(self, content: bytes) -> None:
        self._content = content

    def store_output_archive(
        self,
        *,
        run_id: UUID,
        output_archive: Iterable[bytes],
        reported_artifacts: list[RunnerArtifact],
    ) -> ArtifactsManifest:
        raise NotImplementedError

    def read_artifact(self, *, run_id: UUID, artifact_path: str) -> bytes:
        return self._content


class FakeRuns(ToolRunRepositoryProtocol):
    def __init__(self, runs_by_id: dict[UUID, ToolRun] | None = None) -> None:
        self._runs_by_id = runs_by_id or {}

    async def get_by_id(self, *, run_id: UUID) -> ToolRun | None:
        return self._runs_by_id.get(run_id)

    async def create(self, *, run: ToolRun) -> ToolRun:
        raise NotImplementedError

    async def update(self, *, run: ToolRun) -> ToolRun:
        raise NotImplementedError

    async def get_latest_for_user_and_tool(
        self,
        *,
        user_id: UUID,
        tool_id: UUID,
        context: RunContext,
    ) -> ToolRun | None:
        return None

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        context: RunContext,
        limit: int = 50,
    ) -> list[ToolRun]:
        return []

    async def count_for_user_this_month(
        self,
        *,
        user_id: UUID,
        context: RunContext,
    ) -> int:
        return 0

    async def list_recent_tools_for_user(
        self,
        *,
        user_id: UUID,
        limit: int = 10,
    ) -> list[RecentRunRow]:
        return []


class FakeTools(ToolRepositoryProtocol):
    async def list_by_tags(self, *, profession_id: UUID, category_id: UUID) -> list[Tool]:
        return []

    async def list_all(self) -> list[Tool]:
        return []

    async def list_by_ids(self, *, tool_ids: list[UUID]) -> list[Tool]:
        return []

    async def list_published_filtered(
        self,
        *,
        profession_ids: list[UUID] | None = None,
        category_ids: list[UUID] | None = None,
        search_term: str | None = None,
    ) -> list[Tool]:
        return []

    async def get_by_id(self, *, tool_id: UUID) -> Tool | None:
        return None

    async def get_by_slug(self, *, slug: str) -> Tool | None:
        return None

    async def set_published(self, *, tool_id: UUID, is_published: bool, now: datetime) -> Tool:
        raise NotImplementedError

    async def set_active_version_id(
        self, *, tool_id: UUID, active_version_id: UUID | None, now: datetime
    ) -> Tool:
        raise NotImplementedError

    async def update_metadata(
        self,
        *,
        tool_id: UUID,
        title: str,
        summary: str | None,
        now: datetime,
    ) -> Tool:
        raise NotImplementedError

    async def update_slug(self, *, tool_id: UUID, slug: str, now: datetime) -> Tool:
        raise NotImplementedError

    async def create_draft(
        self,
        *,
        tool: Tool,
        profession_ids: list[UUID],
        category_ids: list[UUID],
    ) -> Tool:
        raise NotImplementedError

    async def list_tag_ids(self, *, tool_id: UUID) -> tuple[list[UUID], list[UUID]]:
        raise NotImplementedError

    async def replace_tags(
        self,
        *,
        tool_id: UUID,
        profession_ids: list[UUID],
        category_ids: list[UUID],
        now: datetime,
    ) -> None:
        raise NotImplementedError


class FakeCuratedApps(CuratedAppRegistryProtocol):
    def list_all(self) -> list[CuratedAppDefinition]:
        return []

    def get_by_app_id(self, *, app_id: str) -> CuratedAppDefinition | None:
        return None

    def get_by_tool_id(self, *, tool_id: UUID) -> CuratedAppDefinition | None:
        return None


class FakeVaultFileRepo(VaultFileRepositoryProtocol):
    def __init__(self) -> None:
        self._files: dict[UUID, VaultFile] = {}

    async def get_by_id(self, *, file_id: UUID) -> VaultFile | None:
        return self._files.get(file_id)

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
        files = [item for item in self._files.values() if item.user_id == user_id]
        if state is VaultListState.ACTIVE:
            files = [item for item in files if item.deleted_at is None]
        else:
            files = [item for item in files if item.deleted_at is not None]

        if search:
            search_lower = search.casefold()
            files = [item for item in files if search_lower in item.name.casefold()]

        if sort is VaultListSort.NAME:
            files = sorted(files, key=lambda item: (item.name.casefold(), str(item.id)))
        elif sort is VaultListSort.SIZE:
            files = sorted(files, key=lambda item: (-item.bytes, str(item.id)), reverse=False)
        else:
            files = sorted(
                files,
                key=lambda item: (item.created_at, str(item.id)),
                reverse=True,
            )

        return files[offset : offset + limit]

    async def list_active_for_user(self, *, user_id: UUID) -> list[VaultFile]:
        return [
            file
            for file in self._files.values()
            if file.user_id == user_id and file.deleted_at is None
        ]

    async def list_by_ids(
        self,
        *,
        user_id: UUID,
        file_ids: list[UUID],
        include_deleted: bool,
    ) -> list[VaultFile]:
        files = [self._files[file_id] for file_id in file_ids if file_id in self._files]
        if not include_deleted:
            files = [file for file in files if file.deleted_at is None]
        return [file for file in files if file.user_id == user_id]

    async def list_expired(self, *, cutoff: datetime, limit: int) -> list[VaultFile]:
        return []

    async def create(self, *, file: VaultFile) -> VaultFile:
        self._files[file.id] = file
        return file

    async def update(self, *, file: VaultFile) -> VaultFile:
        self._files[file.id] = file
        return file

    async def delete(self, *, file_id: UUID) -> None:
        self._files.pop(file_id, None)


class FakeVaultUsageRepo(VaultUsageRepositoryProtocol):
    def __init__(self) -> None:
        self._usage: dict[UUID, VaultUsage] = {}

    async def get(self, *, user_id: UUID) -> VaultUsage | None:
        return self._usage.get(user_id)

    async def get_for_update(self, *, user_id: UUID, now: datetime) -> VaultUsage:
        usage = self._usage.get(
            user_id,
            VaultUsage(user_id=user_id, bytes_total=0, updated_at=now),
        )
        self._usage[user_id] = usage
        return usage

    async def upsert(self, *, usage: VaultUsage) -> VaultUsage:
        self._usage[usage.user_id] = usage
        return usage

    async def recompute_total(self, *, user_id: UUID, now: datetime) -> int:
        usage = self._usage.get(user_id, VaultUsage(user_id=user_id, bytes_total=0, updated_at=now))
        self._usage[user_id] = usage
        return usage.bytes_total


class FakeVaultStorage(VaultStorageProtocol):
    def __init__(self) -> None:
        self._files: dict[tuple[UUID, UUID], bytes] = {}

    async def store_file(self, *, user_id: UUID, file_id: UUID, content: bytes) -> None:
        self._files[(user_id, file_id)] = content

    async def exists_file(self, *, user_id: UUID, file_id: UUID) -> bool:
        return (user_id, file_id) in self._files

    async def read_file(self, *, user_id: UUID, file_id: UUID) -> bytes:
        return self._files[(user_id, file_id)]

    async def delete_file(self, *, user_id: UUID, file_id: UUID) -> None:
        self._files.pop((user_id, file_id), None)


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
