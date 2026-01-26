from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from skriptoteket.application.scripting.vault import (
    DeleteVaultFileCommand,
    DeleteVaultFileResult,
    ListVaultFilesQuery,
    ListVaultFilesResult,
    RestoreVaultFileCommand,
    RestoreVaultFileResult,
    SaveVaultFileCommand,
    SaveVaultFileResult,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault import VaultFile, VaultListSort, VaultListState, VaultUsage


class VaultFileRepositoryProtocol(Protocol):
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

    async def create(self, *, file: VaultFile) -> VaultFile: ...

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
