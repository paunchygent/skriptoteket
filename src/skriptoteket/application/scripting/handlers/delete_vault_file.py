from __future__ import annotations

from skriptoteket.application.scripting.handlers._vault_helpers import build_vault_file_info
from skriptoteket.application.scripting.vault import DeleteVaultFileCommand, DeleteVaultFileResult
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault import VaultUsage
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    DeleteVaultFileHandlerProtocol,
    VaultFileRepositoryProtocol,
    VaultUsageRepositoryProtocol,
)


class DeleteVaultFileHandler(DeleteVaultFileHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._vault_files = vault_files
        self._vault_usage = vault_usage
        self._clock = clock

    async def handle(
        self,
        *,
        actor: User,
        command: DeleteVaultFileCommand,
    ) -> DeleteVaultFileResult:
        now = self._clock.now()
        async with self._uow:
            vault_file = await self._vault_files.get_by_id(file_id=command.file_id)
            if vault_file is None or vault_file.user_id != actor.id:
                raise not_found("VaultFile", str(command.file_id))

            if vault_file.deleted_at is None:
                updated = vault_file.model_copy(update={"deleted_at": now})
                vault_file = await self._vault_files.update(file=updated)

                usage = await self._vault_usage.get_for_update(user_id=actor.id, now=now)
                new_total = max(0, usage.bytes_total - vault_file.bytes)
                await self._vault_usage.upsert(
                    usage=VaultUsage(
                        user_id=actor.id,
                        bytes_total=new_total,
                        updated_at=now,
                    )
                )

        return DeleteVaultFileResult(file=build_vault_file_info(vault_file=vault_file))
