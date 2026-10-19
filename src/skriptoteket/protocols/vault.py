from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from datetime import datetime
from typing import Protocol
from uuid import UUID

from skriptoteket.application.curated_apps.exam_workspace_history import (
    ExamWorkspaceHistoryCursor,
    ExamWorkspaceHistoryStepRef,
    ExamWorkspaceHistoryStoredStep,
)
from skriptoteket.application.scripting.vault import (
    DeleteVaultFileCommand,
    DeleteVaultFileResult,
    ListVaultFilesQuery,
    ListVaultFilesResult,
    RenameVaultFileCommand,
    RenameVaultFileResult,
    RestoreVaultFileCommand,
    RestoreVaultFileResult,
    SaveVaultFileCommand,
    SaveVaultFileResult,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault import VaultFile, VaultListSort, VaultListState, VaultUsage


class VaultFileRepositoryProtocol(Protocol):
    """Stored Mina filer rows, the exam file per lineage, and exam undo history."""

    async def get_by_id(self, *, file_id: UUID) -> VaultFile | None: ...

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        state: VaultListState,
        search: str | None,
        sort: VaultListSort,
        limit: int,
        offset: int,
    ) -> list[VaultFile]: ...

    async def list_active_for_user(self, *, user_id: UUID) -> list[VaultFile]: ...

    async def list_by_ids(
        self,
        *,
        user_id: UUID,
        file_ids: list[UUID],
        include_deleted: bool,
    ) -> list[VaultFile]: ...

    async def list_expired(
        self,
        *,
        cutoff: datetime,
        limit: int,
    ) -> list[VaultFile]: ...

    async def get_document_head(
        self,
        *,
        user_id: UUID,
        document_lineage_id: UUID,
    ) -> VaultFile | None: ...

    async def list_document_heads(
        self,
        *,
        user_id: UUID,
        source_artifact_prefix: str,
    ) -> list[VaultFile]: ...

    async def list_saved_exports(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> list[VaultFile]: ...

    async def list_exam_files(
        self,
        *,
        user_id: UUID,
        document_lineage_id: UUID,
        include_deleted: bool,
    ) -> list[VaultFile]: ...

    async def get_history_head(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> ExamWorkspaceHistoryCursor | None: ...

    async def upsert_history_head(
        self, *, user_id: UUID, document_lineage_id: UUID, head: ExamWorkspaceHistoryCursor
    ) -> None: ...

    async def get_history_step(
        self, *, user_id: UUID, document_lineage_id: UUID, step_id: UUID
    ) -> ExamWorkspaceHistoryStoredStep | None: ...

    async def list_history_step_refs(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> list[ExamWorkspaceHistoryStepRef]: ...

    async def list_history_steps(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> list[ExamWorkspaceHistoryStoredStep]: ...

    async def get_history_assets(
        self, *, user_id: UUID, document_lineage_id: UUID, asset_ids: tuple[str, ...]
    ) -> dict[str, bytes]: ...

    async def insert_history_step(
        self,
        *,
        user_id: UUID,
        document_lineage_id: UUID,
        step: ExamWorkspaceHistoryStoredStep,
        assets_by_id: dict[str, bytes],
    ) -> None: ...

    async def delete_history_steps(
        self, *, user_id: UUID, document_lineage_id: UUID, step_ids: list[UUID]
    ) -> None: ...

    async def delete_orphan_history_assets(
        self, *, user_id: UUID, document_lineage_id: UUID, keep_asset_ids: frozenset[str]
    ) -> None: ...

    async def delete_history(self, *, user_id: UUID, document_lineage_id: UUID) -> None: ...

    async def name_in_use(
        self,
        *,
        user_id: UUID,
        name: str,
        exclude_lineage_id: UUID | None,
        exclude_file_id: UUID | None,
    ) -> bool: ...

    async def lock_owner_renames(self, *, user_id: UUID) -> None: ...

    def guard_document_payload(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> AbstractAsyncContextManager[None]:
        """Exclude payload readers/writers until commit and compensation finish."""
        ...

    async def lock_document_lineage(self, *, user_id: UUID, document_lineage_id: UUID) -> None: ...

    async def lock_lifecycle_rows(
        self,
        *,
        user_id: UUID,
        file_id: UUID,
        document_lineage_id: UUID | None,
    ) -> list[VaultFile]:
        """Return fresh lineage rows, or the plain file, locked in UUID order.

        Callers must hold the lineage lock when a lineage is present and acquire
        usage locks afterward. Row locks remain held until the Unit of Work ends.
        """
        ...

    async def rename_active(
        self, *, user_id: UUID, file_id: UUID, name: str
    ) -> VaultFile | None: ...

    async def rename_lineage(
        self, *, user_id: UUID, document_lineage_id: UUID, name: str
    ) -> list[VaultFile]: ...

    async def create(self, *, file: VaultFile) -> VaultFile: ...

    async def overwrite(self, *, file: VaultFile) -> VaultFile: ...

    async def update(self, *, file: VaultFile) -> VaultFile: ...

    async def delete(self, *, file_id: UUID) -> None: ...


class VaultUsageRepositoryProtocol(Protocol):
    async def get(self, *, user_id: UUID) -> VaultUsage | None: ...

    async def get_for_update(self, *, user_id: UUID, now: datetime) -> VaultUsage: ...

    async def upsert(self, *, usage: VaultUsage) -> VaultUsage: ...

    async def recompute_total(self, *, user_id: UUID, now: datetime) -> int: ...


class VaultStorageProtocol(Protocol):
    async def store_file(
        self,
        *,
        user_id: UUID,
        file_id: UUID,
        content: bytes,
    ) -> None: ...

    async def exists_file(
        self,
        *,
        user_id: UUID,
        file_id: UUID,
    ) -> bool: ...

    async def read_file(
        self,
        *,
        user_id: UUID,
        file_id: UUID,
    ) -> bytes: ...

    async def delete_file(
        self,
        *,
        user_id: UUID,
        file_id: UUID,
    ) -> None: ...


class DownloadVaultFileHandlerProtocol(Protocol):
    async def handle(self, *, actor: User, file_id: UUID) -> tuple[str, bytes]: ...


class ListVaultFilesHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        query: ListVaultFilesQuery,
    ) -> ListVaultFilesResult: ...


class SaveVaultFileHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: SaveVaultFileCommand,
    ) -> SaveVaultFileResult: ...


class DeleteVaultFileHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: DeleteVaultFileCommand,
    ) -> DeleteVaultFileResult: ...


class RestoreVaultFileHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: RestoreVaultFileCommand,
    ) -> RestoreVaultFileResult: ...


class RenameVaultFileHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: RenameVaultFileCommand,
    ) -> RenameVaultFileResult: ...
