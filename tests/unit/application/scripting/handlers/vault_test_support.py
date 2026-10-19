from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from types import TracebackType
from typing import Iterable
from uuid import UUID

from skriptoteket.application.curated_apps.exam_workspace_history import (
    ExamWorkspaceEditLease,
    ExamWorkspaceHistoryCursor,
    ExamWorkspaceHistoryStepRef,
    ExamWorkspaceHistoryStoredStep,
)
from skriptoteket.domain.catalog.models import Tool
from skriptoteket.domain.curated_apps.models import CuratedAppDefinition
from skriptoteket.domain.scripting.artifacts import (
    ArtifactsManifest,
    RunnerArtifact,
)
from skriptoteket.domain.scripting.models import RunContext, ToolRun
from skriptoteket.domain.scripting.vault import (
    VaultFile,
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
        # A saved exam export is listed with its exam, never as its own Mina filer row.
        files = [item for item in files if item.export_format is None]
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

    async def get_document_head(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> VaultFile | None:
        return next(
            (
                file
                for file in self._files.values()
                if file.user_id == user_id
                and file.document_lineage_id == document_lineage_id
                and file.deleted_at is None
                and file.export_format is None
            ),
            None,
        )

    async def list_document_heads(
        self, *, user_id: UUID, source_artifact_prefix: str
    ) -> list[VaultFile]:
        heads = [
            file
            for file in self._files.values()
            if file.user_id == user_id
            and file.document_lineage_id is not None
            and file.deleted_at is None
            and file.export_format is None
            and (file.source_artifact_id or "").startswith(source_artifact_prefix)
        ]
        return sorted(heads, key=lambda file: (file.created_at, str(file.id)), reverse=True)

    async def list_saved_exports(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> list[VaultFile]:
        return [
            file
            for file in self._files.values()
            if file.user_id == user_id
            and file.document_lineage_id == document_lineage_id
            and file.deleted_at is None
            and file.export_format is not None
        ]

    async def list_exam_files(
        self, *, user_id: UUID, document_lineage_id: UUID, include_deleted: bool
    ) -> list[VaultFile]:
        return sorted(
            (
                file
                for file in self._files.values()
                if file.user_id == user_id
                and file.document_lineage_id == document_lineage_id
                and (include_deleted or file.deleted_at is None)
            ),
            key=lambda file: (
                file.export_format is not None,
                file.export_format or "",
                file.created_at,
                str(file.id),
            ),
        )

    async def get_history_head(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> ExamWorkspaceHistoryCursor | None:
        raise NotImplementedError

    async def upsert_history_head(
        self,
        *,
        user_id: UUID,
        document_lineage_id: UUID,
        head: ExamWorkspaceHistoryCursor,
    ) -> None:
        raise NotImplementedError

    async def get_history_lease(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> ExamWorkspaceEditLease | None:
        raise NotImplementedError

    async def upsert_history_lease(
        self, *, user_id: UUID, document_lineage_id: UUID, lease: ExamWorkspaceEditLease
    ) -> None:
        raise NotImplementedError

    async def get_history_step(
        self, *, user_id: UUID, document_lineage_id: UUID, step_id: UUID
    ) -> ExamWorkspaceHistoryStoredStep | None:
        raise NotImplementedError

    async def list_history_step_refs(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> list[ExamWorkspaceHistoryStepRef]:
        raise NotImplementedError

    async def list_history_steps(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> list[ExamWorkspaceHistoryStoredStep]:
        raise NotImplementedError

    async def get_history_assets(
        self, *, user_id: UUID, document_lineage_id: UUID, asset_ids: tuple[str, ...]
    ) -> dict[str, bytes]:
        raise NotImplementedError

    async def insert_history_step(
        self,
        *,
        user_id: UUID,
        document_lineage_id: UUID,
        step: ExamWorkspaceHistoryStoredStep,
        assets_by_id: dict[str, bytes],
    ) -> None:
        raise NotImplementedError

    async def delete_history_steps(
        self, *, user_id: UUID, document_lineage_id: UUID, step_ids: list[UUID]
    ) -> None:
        raise NotImplementedError

    async def delete_orphan_history_assets(
        self, *, user_id: UUID, document_lineage_id: UUID, keep_asset_ids: frozenset[str]
    ) -> None:
        raise NotImplementedError

    async def delete_history(self, *, user_id: UUID, document_lineage_id: UUID) -> None:
        raise NotImplementedError

    async def name_in_use(
        self,
        *,
        user_id: UUID,
        name: str,
        exclude_lineage_id: UUID | None,
        exclude_file_id: UUID | None,
    ) -> bool:
        return any(
            file.user_id == user_id
            and file.name == name
            and file.deleted_at is None
            and file.id != exclude_file_id
            and (exclude_lineage_id is None or file.document_lineage_id != exclude_lineage_id)
            for file in self._files.values()
        )

    @asynccontextmanager
    async def guard_document_payload(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> AsyncIterator[None]:
        """No persistent payloads exist in this unit-only repository."""
        yield

    async def lock_owner_renames(self, *, user_id: UUID) -> None:
        return None

    async def lock_document_lineage(self, *, user_id: UUID, document_lineage_id: UUID) -> None:
        return None

    async def lock_lifecycle_rows(
        self, *, user_id: UUID, file_id: UUID, document_lineage_id: UUID | None
    ) -> list[VaultFile]:
        return sorted(
            (
                file
                for file in self._files.values()
                if file.user_id == user_id
                and (
                    file.document_lineage_id == document_lineage_id
                    if document_lineage_id is not None
                    else file.id == file_id
                )
            ),
            key=lambda file: file.id,
        )

    async def rename_active(self, *, user_id: UUID, file_id: UUID, name: str) -> VaultFile | None:
        file = self._files.get(file_id)
        if file is None or file.user_id != user_id or file.deleted_at is not None:
            return None
        renamed = file.model_copy(update={"name": name})
        self._files[file_id] = renamed
        return renamed

    async def rename_lineage(
        self, *, user_id: UUID, document_lineage_id: UUID, name: str
    ) -> list[VaultFile]:
        renamed = [
            file.model_copy(update={"name": name})
            for file in self._files.values()
            if file.user_id == user_id
            and file.document_lineage_id == document_lineage_id
            and file.export_format is None
        ]
        self._files.update({file.id: file for file in renamed})
        return renamed

    async def create(self, *, file: VaultFile) -> VaultFile:
        self._files[file.id] = file
        return file

    async def update(self, *, file: VaultFile) -> VaultFile:
        current = self._files.get(file.id)
        if current is None:
            return file
        # Lifecycle callers own only trash state; a stale delete/restore payload
        # must not overwrite a concurrently committed name or immutable metadata.
        updated = current.model_copy(
            update={"deleted_at": file.deleted_at, "trashed_with_exam": file.trashed_with_exam}
        )
        self._files[file.id] = updated
        return updated

    async def overwrite(self, *, file: VaultFile) -> VaultFile:
        current = self._files.get(file.id)
        if current is None:
            return file
        overwritten = current.model_copy(
            update={
                "name": file.name,
                "bytes": file.bytes,
                "source_artifact_id": file.source_artifact_id,
                "document_version": file.document_version,
                "export_format": file.export_format,
                "document_saved_at": file.document_saved_at,
            }
        )
        self._files[file.id] = overwritten
        return overwritten

    async def delete(self, *, file_id: UUID) -> None:
        file = self._files.pop(file_id, None)
        if file is None:
            return


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
