from __future__ import annotations

from datetime import timedelta

from skriptoteket.application.scripting.handlers._vault_helpers import build_vault_file_info
from skriptoteket.application.scripting.handlers._vault_lifecycle import lock_vault_lifecycle_target
from skriptoteket.application.scripting.vault import RestoreVaultFileCommand, RestoreVaultFileResult
from skriptoteket.config import Settings
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault import VaultFile, VaultUsage
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
            vault_file = await lock_vault_lifecycle_target(
                vault_files=self._vault_files, user_id=actor.id, file_id=command.file_id
            )
            if vault_file is None:
                raise not_found("VaultFile", str(command.file_id))

            if vault_file.deleted_at is None:
                return RestoreVaultFileResult(file=build_vault_file_info(vault_file=vault_file))

            members = await self._rows_moving_back(actor=actor, target=vault_file)
            cutoff = now - timedelta(days=self._settings.VAULT_RETENTION_DAYS)
            expired = [
                member
                for member in members
                if member.deleted_at is not None and member.deleted_at < cutoff
            ]
            if expired:
                raise validation_error(
                    "Vault file has expired and cannot be restored.",
                    details={
                        "file_id": str(vault_file.id),
                        "expired_file_ids": [str(member.id) for member in expired],
                    },
                )

            # The whole group returns at once, so the quota has to fit all of it: the
            # check runs before any row changes, and a group that does not fit leaves
            # every row in the trash.
            restored_bytes = sum(member.bytes for member in members)
            usage = await self._vault_usage.get_for_update(user_id=actor.id, now=now)
            if usage.bytes_total + restored_bytes > self._settings.VAULT_MAX_TOTAL_BYTES:
                raise validation_error(
                    "Vault quota exceeded.",
                    details={
                        "bytes_total": usage.bytes_total,
                        "attempted_bytes": restored_bytes,
                        "max_total_bytes": self._settings.VAULT_MAX_TOTAL_BYTES,
                    },
                )

            for member in members:
                updated = await self._vault_files.update(
                    file=member.model_copy(update={"deleted_at": None, "trashed_with_exam": False})
                )
                if member.id == command.file_id:
                    # The row the repository wrote back is the answer: a rename that
                    # committed while this request waited keeps its new name here.
                    vault_file = updated
            await self._vault_usage.upsert(
                usage=VaultUsage(
                    user_id=actor.id,
                    bytes_total=usage.bytes_total + restored_bytes,
                    updated_at=now,
                )
            )

        return RestoreVaultFileResult(file=build_vault_file_info(vault_file=vault_file))

    async def _rows_moving_back(self, *, actor: User, target: VaultFile) -> list[VaultFile]:
        """Return the trashed rows that leave the trash together with the target.

        An exam owns its saved exports: restoring the exam restores the exports that were
        trashed with it, while an export the user trashed on its own stays in the trash
        until it is restored by itself. Restoring a saved export whose exam is still in
        the trash returns the owning exam with it, so no active export can sit under a
        trashed exam. A saved export whose exam is active returns alone, so the per-file
        control keeps working. Callers hold the lineage lock, so a save, trash or restore
        of the same exam cannot interleave with this group read.
        """

        lineage_id = target.document_lineage_id
        if lineage_id is None:
            return [target]

        members = await self._vault_files.list_exam_files(
            user_id=actor.id, document_lineage_id=lineage_id, include_deleted=True
        )
        exam_document = next((member for member in members if member.export_format is None), None)
        exam_in_trash = exam_document is not None and exam_document.deleted_at is not None
        if target.export_format is not None and not exam_in_trash:
            return [target]

        together = [
            member
            for member in members
            if member.deleted_at is not None
            and (member.export_format is None or member.trashed_with_exam)
        ]
        if all(member.id != target.id for member in together):
            together.append(target)
        return together
