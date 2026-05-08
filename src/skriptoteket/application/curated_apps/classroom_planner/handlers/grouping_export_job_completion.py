"""Completion helpers for classroom-planner grouping export jobs.

Purpose:
    Keep Vault persistence and terminal job updates separate from grouping
    export orchestration so the create-job handler can stay focused on choosing
    the correct export lane.

Relationships:
    - Consumed by the grouping XLSX and local PDF export paths in
      `handlers.grouping_export_jobs`.
    - Uses the dedicated grouping export-job repository plus Vault protocols.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    GroupingExportJob,
    GroupingExportJobStatus,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.classroom_planner.grouping_checkpoints import (
    GroupingExportCheckpoint,
)
from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.scripting.input_files import sanitize_input_filename
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind, VaultUsage
from skriptoteket.protocols.classroom_planner_exports import GroupingExportJobRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)

from .checkpoint_recorders import GroupingCheckpointRecorder


class GroupingExportJobFinalizer:
    """Persist locally generated grouping artifacts and terminal job states."""

    def __init__(
        self,
        *,
        jobs: GroupingExportJobRepositoryProtocol,
        checkpoint_recorder: GroupingCheckpointRecorder,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        settings: Settings,
    ) -> None:
        self._jobs = jobs
        self._checkpoint_recorder = checkpoint_recorder
        self._vault_files = vault_files
        self._vault_usage = vault_usage
        self._vault_storage = vault_storage
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator
        self._settings = settings

    async def complete_local_success(
        self,
        *,
        job: GroupingExportJob,
        content: bytes,
        checkpoint: GroupingExportCheckpoint | None = None,
        filename: str | None = None,
    ) -> GroupingExportJob:
        """Persist one locally generated artifact and complete the export job."""

        vault_file = await self._save_to_vault(
            owner_user_id=job.owner_user_id,
            filename=filename or job.output_filename,
            content=content,
        )
        return await self._persist_terminal_status(
            job=job,
            status=GroupingExportJobStatus.SUCCEEDED,
            vault_file_id=vault_file.id,
            error_message=None,
            checkpoint=checkpoint,
        )

    async def mark_failed(
        self,
        *,
        job: GroupingExportJob,
        error_message: str,
    ) -> GroupingExportJob:
        """Persist a terminal failed state for one export job."""

        return await self._persist_terminal_status(
            job=job,
            status=GroupingExportJobStatus.FAILED,
            vault_file_id=job.vault_file_id,
            error_message=error_message,
            checkpoint=None,
        )

    async def _persist_terminal_status(
        self,
        *,
        job: GroupingExportJob,
        status: GroupingExportJobStatus,
        vault_file_id: UUID | None,
        error_message: str | None,
        checkpoint: GroupingExportCheckpoint | None,
    ) -> GroupingExportJob:
        updated = job.model_copy(
            update={
                "status": status,
                "vault_file_id": vault_file_id,
                "error_message": error_message,
            }
        )
        async with self._uow:
            persisted_job = await self._jobs.update(job=updated)
            if checkpoint is not None and status is GroupingExportJobStatus.SUCCEEDED:
                await self._checkpoint_recorder.record(checkpoint=checkpoint)
            return persisted_job

    async def _save_to_vault(
        self,
        *,
        owner_user_id: UUID,
        filename: str,
        content: bytes,
    ) -> VaultFile:
        actual_bytes = len(content)
        if actual_bytes > self._settings.VAULT_MAX_FILE_BYTES:
            raise validation_error("Exportfilen är för stor för Vault.")
        safe_name = sanitize_input_filename(input_filename=filename or "klassrumskarta-export")
        now = self._clock.now()
        file_id = self._id_generator.new_uuid()

        stored = False
        try:
            async with self._uow:
                usage = await self._vault_usage.get_for_update(user_id=owner_user_id, now=now)
                if usage.bytes_total + actual_bytes > self._settings.VAULT_MAX_TOTAL_BYTES:
                    raise validation_error("Vault-utrymmet är fullt.")
                vault_file = await self._vault_files.create(
                    file=VaultFile(
                        id=file_id,
                        user_id=owner_user_id,
                        name=safe_name,
                        bytes=actual_bytes,
                        source_kind=VaultFileSourceKind.APP_EXPORT,
                        source_run_id=None,
                        source_artifact_id="classroom.group-seating-studio",
                        created_at=now,
                        deleted_at=None,
                    )
                )
                await self._vault_storage.store_file(
                    user_id=owner_user_id,
                    file_id=vault_file.id,
                    content=content,
                )
                stored = True
                await self._vault_usage.upsert(
                    usage=VaultUsage(
                        user_id=owner_user_id,
                        bytes_total=usage.bytes_total + actual_bytes,
                        updated_at=now,
                    )
                )
                return vault_file
        except Exception:
            if stored:
                await self._vault_storage.delete_file(user_id=owner_user_id, file_id=file_id)
            raise
