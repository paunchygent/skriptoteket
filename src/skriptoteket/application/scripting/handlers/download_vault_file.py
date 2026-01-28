from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    DownloadVaultFileHandlerProtocol,
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
)


class DownloadVaultFileHandler(DownloadVaultFileHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
    ) -> None:
        self._uow = uow
        self._vault_files = vault_files
        self._vault_storage = vault_storage

    async def handle(self, *, actor: User, file_id: UUID) -> tuple[str, bytes]:
        async with self._uow:
            vault_file = await self._vault_files.get_by_id(file_id=file_id)
            if vault_file is None or vault_file.user_id != actor.id:
                raise not_found("VaultFile", str(file_id))

        try:
            content = await self._vault_storage.read_file(
                user_id=actor.id,
                file_id=vault_file.id,
            )
        except FileNotFoundError as exc:
            raise not_found("VaultFile", str(file_id)) from exc

        return vault_file.name, content
