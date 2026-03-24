"""Completion and download handlers for classroom-planner seating export jobs.

Purpose:
    Keep webhook completion, Vault persistence, and download delivery separate
    from export-job submission/orchestration so the PR-0119 handlers stay under
    the repo's module-size budget and preserve single responsibility.

Relationships:
    - Consumed by the internal Sir Convert callback route and the public
      seating export download route.
    - Uses the dedicated seating export-job repository plus Vault protocols.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    SeatingExportJob,
    SeatingExportJobStatus,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.input_files import sanitize_input_filename
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind, VaultUsage
from skriptoteket.protocols.classroom_planner_exports import SeatingExportJobRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.sir_convert_a_lot_v2 import SirConvertALotClientV2Protocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)

from .seating_export_job_support import parse_webhook_payload, verify_webhook_signature


class SeatingExportJobFinalizer:
    """Finalize completed or failed seating export jobs from upstream outcomes."""

    def __init__(
        self,
        *,
        jobs: SeatingExportJobRepositoryProtocol,
        client: SirConvertALotClientV2Protocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        settings: Settings,
    ) -> None:
        self._jobs = jobs
        self._client = client
        self._vault_files = vault_files
        self._vault_usage = vault_usage
        self._vault_storage = vault_storage
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator
        self._settings = settings

    async def complete_success(
        self,
        *,
        job: SeatingExportJob,
        correlation_id: str | None,
    ) -> SeatingExportJob:
        """Download the finished artifact, save it to Vault, and complete the job."""

        if job.upstream_job_id is None:
            raise validation_error("PDF-exporten saknar ett upstream-jobb.")
        if job.status is SeatingExportJobStatus.SUCCEEDED and job.vault_file_id is not None:
            return job

        outcome = await self._client.download_artifact(
            job.upstream_job_id,
            correlation_id=correlation_id,
        )
        vault_file = await self._save_to_vault(
            owner_user_id=job.owner_user_id,
            filename=job.output_filename or outcome.artifact.filename,
            content=outcome.artifact.content,
        )
        return await self._persist_terminal_status(
            job=job,
            status=SeatingExportJobStatus.SUCCEEDED,
            vault_file_id=vault_file.id,
            error_message=None,
            correlation_id=correlation_id,
        )

    async def mark_failed(
        self,
        *,
        job: SeatingExportJob,
        error_message: str,
        correlation_id: str | None,
    ) -> SeatingExportJob:
        """Persist a terminal failed state and clean up the webhook subscription."""

        return await self._persist_terminal_status(
            job=job,
            status=SeatingExportJobStatus.FAILED,
            vault_file_id=job.vault_file_id,
            error_message=error_message,
            correlation_id=correlation_id,
        )

    async def _persist_terminal_status(
        self,
        *,
        job: SeatingExportJob,
        status: SeatingExportJobStatus,
        vault_file_id: UUID | None,
        error_message: str | None,
        correlation_id: str | None,
    ) -> SeatingExportJob:
        del correlation_id
        updated = job.model_copy(
            update={
                "status": status,
                "vault_file_id": vault_file_id,
                "error_message": error_message,
            }
        )
        async with self._uow:
            return await self._jobs.update(job=updated)

    async def _save_to_vault(
        self,
        *,
        owner_user_id: UUID,
        filename: str,
        content: bytes,
    ) -> VaultFile:
        actual_bytes = len(content)
        if actual_bytes > self._settings.VAULT_MAX_FILE_BYTES:
            raise validation_error("PDF-exporten är för stor för Vault.")
        safe_name = sanitize_input_filename(input_filename=filename or "klassrumskarta.pdf")
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


class CompleteSeatingExportJobFromWebhookHandler:
    """Finalize an export job from a signed Sir Convert webhook callback."""

    def __init__(
        self,
        *,
        jobs: SeatingExportJobRepositoryProtocol,
        finalizer: SeatingExportJobFinalizer,
        uow: UnitOfWorkProtocol,
    ) -> None:
        self._jobs = jobs
        self._finalizer = finalizer
        self._uow = uow

    async def handle(
        self,
        *,
        headers: dict[str, str],
        raw_body: bytes,
        correlation_id: str | None,
        callback_job_id_hint: UUID | None = None,
    ) -> None:
        payload = parse_webhook_payload(raw_body)
        async with self._uow:
            job = await self._jobs.get_by_upstream_job_id(upstream_job_id=payload["job_id"])
        if job is None:
            return
        if callback_job_id_hint is not None and job.id != callback_job_id_hint:
            return
        if job.webhook_secret is None:
            return
        verify_webhook_signature(secret=job.webhook_secret, headers=headers, raw_body=raw_body)
        if job.status in {SeatingExportJobStatus.SUCCEEDED, SeatingExportJobStatus.FAILED}:
            return

        if payload["event_type"] == "job.succeeded":
            await self._finalizer.complete_success(
                job=job,
                correlation_id=correlation_id,
            )
        else:
            await self._finalizer.mark_failed(
                job=job,
                error_message="PDF-exporten kunde inte slutföras.",
                correlation_id=correlation_id,
            )


class DownloadSeatingExportJobHandler:
    """Download the finished PDF for one completed seating export job."""

    def __init__(
        self,
        *,
        jobs: SeatingExportJobRepositoryProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        uow: UnitOfWorkProtocol,
    ) -> None:
        self._jobs = jobs
        self._vault_files = vault_files
        self._vault_storage = vault_storage
        self._uow = uow

    async def handle(self, *, actor: User, job_id: UUID) -> tuple[str, bytes]:
        async with self._uow:
            job = await self._jobs.get_by_id(job_id=job_id)
            if job is None or job.owner_user_id != actor.id:
                raise not_found("SeatingExportJob", str(job_id))
            if job.vault_file_id is None:
                raise validation_error("PDF-exporten är inte klar ännu.")
            vault_file = await self._vault_files.get_by_id(file_id=job.vault_file_id)
            if vault_file is None or vault_file.user_id != actor.id:
                raise not_found("VaultFile", str(job.vault_file_id))
        return vault_file.name, await self._vault_storage.read_file(
            user_id=actor.id,
            file_id=vault_file.id,
        )
