from __future__ import annotations

from datetime import datetime, timezone
from types import TracebackType
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.scripting.handlers.list_vault_files import ListVaultFilesHandler
from skriptoteket.application.scripting.vault import ListVaultFilesQuery
from skriptoteket.config import Settings
from skriptoteket.domain.catalog.models import Tool
from skriptoteket.domain.curated_apps.models import CuratedAppDefinition
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.models import RunContext, ToolRun
from skriptoteket.domain.scripting.vault import (
    VaultFile,
    VaultFileSourceKind,
    VaultListSort,
    VaultListState,
    VaultUsage,
)
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.scripting import RecentRunRow, ToolRunRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)
from tests.fixtures.identity_fixtures import make_user


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


class FakeVaultFiles(VaultFileRepositoryProtocol):
    def __init__(self, files: list[VaultFile]) -> None:
        self._files = files

    async def get_by_id(self, *, file_id: UUID) -> VaultFile | None:
        for file in self._files:
            if file.id == file_id:
                return file
        return None

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
        return self._files

    async def list_active_for_user(self, *, user_id: UUID) -> list[VaultFile]:
        raise NotImplementedError

    async def list_by_ids(
        self,
        *,
        user_id: UUID,
        file_ids: list[UUID],
        include_deleted: bool,
    ) -> list[VaultFile]:
        raise NotImplementedError

    async def list_expired(self, *, cutoff: datetime, limit: int) -> list[VaultFile]:
        raise NotImplementedError

    async def create(self, *, file: VaultFile) -> VaultFile:
        raise NotImplementedError

    async def update(self, *, file: VaultFile) -> VaultFile:
        raise NotImplementedError

    async def delete(self, *, file_id: UUID) -> None:
        raise NotImplementedError


class FakeVaultUsage(VaultUsageRepositoryProtocol):
    def __init__(self, usage: VaultUsage) -> None:
        self._usage = usage

    async def get(self, *, user_id: UUID) -> VaultUsage | None:
        return self._usage

    async def get_for_update(self, *, user_id: UUID, now: datetime) -> VaultUsage:
        raise NotImplementedError

    async def upsert(self, *, usage: VaultUsage) -> VaultUsage:
        raise NotImplementedError

    async def recompute_total(self, *, user_id: UUID, now: datetime) -> int:
        raise NotImplementedError


class FakeVaultStorage(VaultStorageProtocol):
    def __init__(self, *, missing_ids: set[UUID]) -> None:
        self._missing_ids = missing_ids

    async def store_file(self, *, user_id: UUID, file_id: UUID, content: bytes) -> None:
        raise NotImplementedError

    async def exists_file(self, *, user_id: UUID, file_id: UUID) -> bool:
        return file_id not in self._missing_ids

    async def read_file(self, *, user_id: UUID, file_id: UUID) -> bytes:
        raise NotImplementedError

    async def delete_file(self, *, user_id: UUID, file_id: UUID) -> None:
        raise NotImplementedError


class FakeRuns(ToolRunRepositoryProtocol):
    async def get_by_id(self, *, run_id: UUID) -> ToolRun | None:
        return None

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
        raise NotImplementedError

    async def list_all(self) -> list[Tool]:
        raise NotImplementedError

    async def list_by_ids(self, *, tool_ids: list[UUID]) -> list[Tool]:
        return []

    async def list_published_filtered(
        self,
        *,
        profession_ids: list[UUID] | None = None,
        category_ids: list[UUID] | None = None,
        search_term: str | None = None,
    ) -> list[Tool]:
        raise NotImplementedError

    async def get_by_id(self, *, tool_id: UUID) -> Tool | None:
        raise NotImplementedError

    async def get_by_slug(self, *, slug: str) -> Tool | None:
        raise NotImplementedError

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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_vault_files_marks_files_missing_on_disk() -> None:
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    actor = make_user(role=Role.USER, user_id=uuid4())

    missing_id = uuid4()
    present_id = uuid4()

    files = [
        VaultFile(
            id=missing_id,
            user_id=actor.id,
            name="missing.pdf",
            bytes=10,
            source_kind=VaultFileSourceKind.APP_EXPORT,
            source_run_id=None,
            source_artifact_id="chemistry.reagent_prep_chef",
            created_at=now,
            deleted_at=None,
        ),
        VaultFile(
            id=present_id,
            user_id=actor.id,
            name="present.pdf",
            bytes=10,
            source_kind=VaultFileSourceKind.APP_EXPORT,
            source_run_id=None,
            source_artifact_id="chemistry.reagent_prep_chef",
            created_at=now,
            deleted_at=None,
        ),
    ]

    handler = ListVaultFilesHandler(
        uow=FakeUow(),
        runs=FakeRuns(),
        tools=FakeTools(),
        curated_apps=FakeCuratedApps(),
        vault_files=FakeVaultFiles(files),
        vault_usage=FakeVaultUsage(VaultUsage(user_id=actor.id, bytes_total=20, updated_at=now)),
        vault_storage=FakeVaultStorage(missing_ids={missing_id}),
        settings=Settings(VAULT_MAX_TOTAL_BYTES=1000, VAULT_MAX_FILE_BYTES=1000),
    )

    result = await handler.handle(
        actor=actor, query=ListVaultFilesQuery(state=VaultListState.ACTIVE)
    )

    assert {item.id for item in result.files} == {missing_id, present_id}
    by_id = {item.id: item for item in result.files}
    assert by_id[missing_id].is_missing_on_disk is True
    assert by_id[present_id].is_missing_on_disk is False
