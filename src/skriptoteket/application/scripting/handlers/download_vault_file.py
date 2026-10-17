from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault import VaultFile
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

        lineage_id = vault_file.document_lineage_id
        if lineage_id is None:
            return await self._read(actor=actor, vault_file=vault_file)

        # Reread metadata and bytes together after any pending write/compensation.
        # The initial lookup only locates the owning lineage; it is not a snapshot.
        async with self._vault_files.guard_document_payload(
            user_id=actor.id, document_lineage_id=lineage_id
        ):
            async with self._uow:
                await self._vault_files.lock_document_lineage(
                    user_id=actor.id, document_lineage_id=lineage_id
                )
                current = await self._vault_files.get_by_id(file_id=file_id)
                if current is None or current.user_id != actor.id:
                    raise not_found("VaultFile", str(file_id))
                return await self._read(actor=actor, vault_file=current)

    async def _read(self, *, actor: User, vault_file: VaultFile) -> tuple[str, bytes]:
        try:
            content = await self._vault_storage.read_file(
                user_id=actor.id,
                file_id=vault_file.id,
            )
        except FileNotFoundError as exc:
            raise not_found("VaultFile", str(vault_file.id)) from exc

        return vault_file.name, content
