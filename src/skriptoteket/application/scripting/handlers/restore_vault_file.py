from __future__ import annotations

from datetime import timedelta

from skriptoteket.application.scripting.handlers._vault_helpers import build_vault_file_info
from skriptoteket.application.scripting.vault import RestoreVaultFileCommand, RestoreVaultFileResult
from skriptoteket.config import Settings
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault import VaultUsage
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    RestoreVaultFileHandlerProtocol,
    VaultFileRepositoryProtocol,
    VaultUsageRepositoryProtocol,
)


class RestoreVaultFileHandler(RestoreVaultFileHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        settings: Settings,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._vault_files = vault_files
        self._vault_usage = vault_usage
        self._settings = settings
        self._clock = clock

    async def handle(
        self,
        *,
        actor: User,
        command: RestoreVaultFileCommand,
    ) -> RestoreVaultFileResult:
        now = self._clock.now()
        async with self._uow:
            vault_file = await self._vault_files.get_by_id(file_id=command.file_id)
            if vault_file is None or vault_file.user_id != actor.id:
                raise not_found("VaultFile", str(command.file_id))

            if vault_file.deleted_at is None:
                return RestoreVaultFileResult(file=build_vault_file_info(vault_file=vault_file))

            cutoff = now - timedelta(days=self._settings.VAULT_RETENTION_DAYS)
            if vault_file.deleted_at < cutoff:
                raise validation_error(
                    "Vault file has expired and cannot be restored.",
                    details={"file_id": str(vault_file.id)},
                )

            usage = await self._vault_usage.get_for_update(user_id=actor.id, now=now)
            if usage.bytes_total + vault_file.bytes > self._settings.VAULT_MAX_TOTAL_BYTES:
                raise validation_error(
                    "Vault quota exceeded.",
                    details={
                        "bytes_total": usage.bytes_total,
                        "attempted_bytes": vault_file.bytes,
                        "max_total_bytes": self._settings.VAULT_MAX_TOTAL_BYTES,
                    },
                )

            updated = vault_file.model_copy(update={"deleted_at": None})
            vault_file = await self._vault_files.update(file=updated)
            await self._vault_usage.upsert(
                usage=VaultUsage(
                    user_id=actor.id,
                    bytes_total=usage.bytes_total + vault_file.bytes,
                    updated_at=now,
                )
            )

        return RestoreVaultFileResult(file=build_vault_file_info(vault_file=vault_file))
