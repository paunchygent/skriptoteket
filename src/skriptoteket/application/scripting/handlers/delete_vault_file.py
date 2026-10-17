from __future__ import annotations

from skriptoteket.application.scripting.handlers._vault_helpers import build_vault_file_info
from skriptoteket.application.scripting.handlers._vault_lifecycle import lock_vault_lifecycle_target
from skriptoteket.application.scripting.vault import DeleteVaultFileCommand, DeleteVaultFileResult
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault import VaultFile, VaultUsage
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
            vault_file = await lock_vault_lifecycle_target(
                vault_files=self._vault_files, user_id=actor.id, file_id=command.file_id
            )
            if vault_file is None:
                raise not_found("VaultFile", str(command.file_id))

            if vault_file.deleted_at is None:
                members = await self._rows_moving_to_trash(actor=actor, target=vault_file)
                # An export that goes to the trash with its exam is marked as such, so
                # the exam's restore knows it came along; a file the user trashed on its
                # own is not, and stays in the trash when the exam returns.
                trashed_with_exam = (
                    vault_file.document_lineage_id is not None and vault_file.export_format is None
                )
                # Only rows that are still active release their bytes: an export that
                # already went to the trash was accounted for when it moved.
                released_bytes = sum(member.bytes for member in members)
                usage = await self._vault_usage.get_for_update(user_id=actor.id, now=now)
                for member in members:
                    updated = await self._vault_files.update(
                        file=member.model_copy(
                            update={
                                "deleted_at": now,
                                "trashed_with_exam": trashed_with_exam,
                            }
                        )
                    )
                    if member.id == command.file_id:
                        # The row the repository wrote back is the answer: a rename that
                        # committed while this request waited keeps its new name here.
                        vault_file = updated
                await self._vault_usage.upsert(
                    usage=VaultUsage(
                        user_id=actor.id,
                        bytes_total=max(0, usage.bytes_total - released_bytes),
                        updated_at=now,
                    )
                )

        return DeleteVaultFileResult(file=build_vault_file_info(vault_file=vault_file))

    async def _rows_moving_to_trash(self, *, actor: User, target: VaultFile) -> list[VaultFile]:
        """Return the active rows that move to the trash together with the target.

        An exam takes its saved exports with it, because they belong to it. A plain file
        or a saved export moves alone, so the per-file control keeps working. Callers
        hold the lineage lock, so a save, trash or restore of the same exam cannot
        interleave with this group read.
        """

        lineage_id = target.document_lineage_id
        if lineage_id is None or target.export_format is not None:
            return [target]

        members = await self._vault_files.list_exam_files(
            user_id=actor.id, document_lineage_id=lineage_id, include_deleted=False
        )
        active = [member for member in members if member.deleted_at is None]
        return active or [target]
