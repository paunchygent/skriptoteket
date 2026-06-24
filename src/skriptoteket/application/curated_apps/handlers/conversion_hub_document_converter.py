"""Document Converter handlers for scoped Conversion Hub artifacts.

Purpose:
    Authorize Document Converter status, downloads, and Mina filer saves by the
    local owner-scoped job id while keeping Sir Convert credentials and artifact
    authority on the server.

Relationships:
    Uses the Conversion Hub local job repository and Sir Convert v2 client for
    producer state, then persists the single converted document through Vault
    ``APP_EXPORT`` records.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubJobStatus,
)
from skriptoteket.application.curated_apps.conversion_hub_saved_artifacts import (
    ConversionHubSavedVaultArtifact,
)
from skriptoteket.application.curated_apps.document_converter import (
    DocumentConverterJobStatusResult,
    DocumentConverterStoredArtifact,
    SaveDocumentConverterArtifactResult,
    build_document_converter_result_artifact,
    build_document_converter_source_artifact_id,
    is_document_converter_job,
    is_local_document_converter_job,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.input_files import sanitize_input_filename
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind, VaultUsage
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.conversion_hub import ConversionHubJobRepositoryProtocol
from skriptoteket.protocols.document_converter import DocumentConverterArtifactStoreProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.sir_convert_a_lot_v2 import (
    SirConvertALotClientV2Protocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)

_TERMINAL_STATUSES = frozenset(
    {
        ConversionHubJobStatus.SUCCEEDED,
        ConversionHubJobStatus.FAILED,
        ConversionHubJobStatus.CANCELED,
    }
)
_UPSTREAM_FAILURE_MESSAGE = "Konverteringen kunde inte slutföras."


class _DocumentConverterJobAccess:
    """Load, refresh, and route-scope local Conversion Hub jobs."""

    def __init__(
        self,
        *,
        jobs: ConversionHubJobRepositoryProtocol,
        client: SirConvertALotClientV2Protocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._jobs = jobs
        self._client = client
        self._uow = uow
        self._clock = clock

    async def load_refreshed(
        self,
        *,
        actor: User,
        job_id: UUID,
        correlation_id: str | None,
    ) -> ConversionHubJob:
        job = await self._load_owned_job(actor=actor, job_id=job_id)
        if not is_document_converter_job(job):
            raise not_found("ConversionHubJob", str(job_id))
        return await self._refresh_job(job=job, correlation_id=correlation_id)

    async def _load_owned_job(self, *, actor: User, job_id: UUID) -> ConversionHubJob:
        async with self._uow:
            job = await self._jobs.get_by_id(job_id=job_id)
        if job is None or job.owner_user_id != actor.id:
            raise not_found("ConversionHubJob", str(job_id))
        return job

    async def _refresh_job(
        self,
        *,
        job: ConversionHubJob,
        correlation_id: str | None,
    ) -> ConversionHubJob:
        if job.status in _TERMINAL_STATUSES or job.upstream_job_id is None:
            return job

        upstream = await self._client.get_job(job.upstream_job_id, correlation_id=correlation_id)
        refreshed_status = ConversionHubJobStatus.from_upstream(upstream.status)
        if refreshed_status is job.status:
            return job

        error_message = None
        if refreshed_status is ConversionHubJobStatus.FAILED:
            error_message = _UPSTREAM_FAILURE_MESSAGE

        async with self._uow:
            return await self._jobs.update(
                job=job.model_copy(
                    update={
                        "status": refreshed_status,
                        "error_message": error_message,
                        "updated_at": self._clock.now(),
                    }
                )
            )


class GetDocumentConverterJobHandler:
    """Load one owner-scoped Document Converter job status."""

    def __init__(
        self,
        *,
        jobs: ConversionHubJobRepositoryProtocol,
        client: SirConvertALotClientV2Protocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._access = _DocumentConverterJobAccess(
            jobs=jobs,
            client=client,
            uow=uow,
            clock=clock,
        )

    async def handle(
        self,
        *,
        actor: User,
        job_id: UUID,
        correlation_id: str | None,
    ) -> DocumentConverterJobStatusResult:
        job = await self._access.load_refreshed(
            actor=actor,
            job_id=job_id,
            correlation_id=correlation_id,
        )
        return DocumentConverterJobStatusResult(
            job_id=job.id,
            status=job.status,
            error=job.error_message,
            result_artifact=build_document_converter_result_artifact(job=job),
        )


class DownloadDocumentConverterArtifactHandler:
    """Authorize and proxy the single Document Converter result artifact."""

    def __init__(
        self,
        *,
        jobs: ConversionHubJobRepositoryProtocol,
        client: SirConvertALotClientV2Protocol,
        local_artifacts: DocumentConverterArtifactStoreProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._access = _DocumentConverterJobAccess(
            jobs=jobs,
            client=client,
            uow=uow,
            clock=clock,
        )
        self._client = client
        self._local_artifacts = local_artifacts

    async def handle(
        self,
        *,
        actor: User,
        job_id: UUID,
        correlation_id: str | None,
    ) -> tuple[str, str, bytes]:
        job = await self._access.load_refreshed(
            actor=actor,
            job_id=job_id,
            correlation_id=correlation_id,
        )
        artifact = await self._download_ready_artifact(job=job, correlation_id=correlation_id)
        return (
            artifact.filename,
            artifact.content_type,
            artifact.content,
        )

    async def _download_ready_artifact(
        self,
        *,
        job: ConversionHubJob,
        correlation_id: str | None,
    ) -> DocumentConverterStoredArtifact:
        _assert_ready_for_artifact(job=job)
        if is_local_document_converter_job(job):
            return self._local_artifacts.read_artifact(job_id=job.id)
        artifact = await self._client.download_artifact(
            job.upstream_job_id or "",
            correlation_id=correlation_id,
        )
        return DocumentConverterStoredArtifact(
            filename=artifact.artifact.filename,
            content_type=artifact.artifact.content_type,
            content=artifact.artifact.content,
        )


class SaveDocumentConverterArtifactHandler:
    """Save the single server-authorized Document Converter result to Vault."""

    def __init__(
        self,
        *,
        jobs: ConversionHubJobRepositoryProtocol,
        client: SirConvertALotClientV2Protocol,
        local_artifacts: DocumentConverterArtifactStoreProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        settings: Settings,
    ) -> None:
        self._access = _DocumentConverterJobAccess(
            jobs=jobs,
            client=client,
            uow=uow,
            clock=clock,
        )
        self._client = client
        self._local_artifacts = local_artifacts
        self._vault_files = vault_files
        self._vault_usage = vault_usage
        self._vault_storage = vault_storage
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator
        self._settings = settings

    async def handle(
        self,
        *,
        actor: User,
        job_id: UUID,
        correlation_id: str | None,
    ) -> SaveDocumentConverterArtifactResult:
        job = await self._access.load_refreshed(
            actor=actor,
            job_id=job_id,
            correlation_id=correlation_id,
        )
        _assert_ready_for_artifact(job=job)
        if is_local_document_converter_job(job):
            artifact = self._local_artifacts.read_artifact(job_id=job.id)
        else:
            producer_artifact = await self._client.download_artifact(
                job.upstream_job_id or "",
                correlation_id=correlation_id,
            )
            artifact = DocumentConverterStoredArtifact(
                filename=producer_artifact.artifact.filename,
                content_type=producer_artifact.artifact.content_type,
                content=producer_artifact.artifact.content,
            )
        return await self._save_artifact(actor=actor, job=job, artifact=artifact)

    async def _save_artifact(
        self,
        *,
        actor: User,
        job: ConversionHubJob,
        artifact: DocumentConverterStoredArtifact,
    ) -> SaveDocumentConverterArtifactResult:
        filename = sanitize_input_filename(input_filename=artifact.filename)
        content_type = artifact.content_type.strip()
        if not content_type:
            raise validation_error("Konverteringsresultatet saknar filtyp.")

        content = artifact.content
        actual_bytes = len(content)
        if actual_bytes <= 0:
            raise validation_error("Filen saknar innehåll.")
        if actual_bytes > self._settings.VAULT_MAX_FILE_BYTES:
            raise validation_error(
                "Vault file exceeds the max file size.",
                details={
                    "bytes": actual_bytes,
                    "max_bytes": self._settings.VAULT_MAX_FILE_BYTES,
                },
            )

        now = self._clock.now()
        file_id = self._id_generator.new_uuid()
        source_artifact_id = build_document_converter_source_artifact_id(
            upstream_job_id=job.upstream_job_id or ""
        )
        stored = False

        try:
            async with self._uow:
                usage = await self._vault_usage.get_for_update(user_id=actor.id, now=now)
                if usage.bytes_total + actual_bytes > self._settings.VAULT_MAX_TOTAL_BYTES:
                    raise validation_error(
                        "Vault quota exceeded.",
                        details={
                            "bytes_total": usage.bytes_total,
                            "attempted_bytes": actual_bytes,
                            "max_total_bytes": self._settings.VAULT_MAX_TOTAL_BYTES,
                        },
                    )
                vault_file = await self._vault_files.create(
                    file=VaultFile(
                        id=file_id,
                        user_id=actor.id,
                        name=filename,
                        bytes=actual_bytes,
                        source_kind=VaultFileSourceKind.APP_EXPORT,
                        source_run_id=None,
                        source_artifact_id=source_artifact_id,
                        created_at=now,
                        deleted_at=None,
                    )
                )
                await self._vault_storage.store_file(
                    user_id=actor.id,
                    file_id=vault_file.id,
                    content=content,
                )
                stored = True
                await self._vault_usage.upsert(
                    usage=VaultUsage(
                        user_id=actor.id,
                        bytes_total=usage.bytes_total + actual_bytes,
                        updated_at=now,
                    )
                )
        except Exception:
            if stored:
                await self._vault_storage.delete_file(user_id=actor.id, file_id=file_id)
            raise

        return SaveDocumentConverterArtifactResult(
            vault_artifact=ConversionHubSavedVaultArtifact(
                file_id=vault_file.id,
                name=vault_file.name,
                bytes=vault_file.bytes,
                created_at=vault_file.created_at,
            ),
            source_artifact_id=source_artifact_id,
        )


def _assert_ready_for_artifact(*, job: ConversionHubJob) -> None:
    if job.status is not ConversionHubJobStatus.SUCCEEDED:
        if job.status is ConversionHubJobStatus.FAILED:
            raise validation_error(job.error_message or _UPSTREAM_FAILURE_MESSAGE)
        if job.status is ConversionHubJobStatus.CANCELED:
            raise validation_error("Konverteringen avbröts innan filen blev klar.")
        raise validation_error("Konverteringen är inte klar ännu.")
    if job.upstream_job_id is None:
        raise validation_error("Konverteringen saknar nedladdningsbar artefakt.")
