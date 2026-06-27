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
from skriptoteket.application.curated_apps.document_converter import (
    DocumentConverterJobStatusResult,
    DocumentConverterStoredArtifact,
    SaveDocumentConverterArtifactResult,
    build_document_converter_result_artifact,
    build_document_converter_source_artifact_id,
    is_document_converter_job,
    is_local_document_converter_job,
)
from skriptoteket.application.curated_apps.document_converter_file_naming import (
    apply_single_file_protocol_filename,
)
from skriptoteket.application.curated_apps.handlers.document_converter_vault_saves import (
    DocumentConverterVaultSaveService,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.domain.identity.models import User
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
        refreshed_status = ConversionHubJobStatus.from_sir_convert_status(upstream.status)
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
        filename_stem: str | None = None,
    ) -> tuple[str, str, bytes]:
        job = await self._access.load_refreshed(
            actor=actor,
            job_id=job_id,
            correlation_id=correlation_id,
        )
        artifact = await self._download_ready_artifact(job=job, correlation_id=correlation_id)
        artifact = apply_single_file_protocol_filename(
            artifact=artifact,
            input_filename=job.input_filename,
            output_format=job.output_format,
            created_at=job.created_at,
            filename_stem=filename_stem,
        )
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
        self._vault_saves = DocumentConverterVaultSaveService(
            vault_files=vault_files,
            vault_usage=vault_usage,
            vault_storage=vault_storage,
            uow=uow,
            clock=clock,
            id_generator=id_generator,
            settings=settings,
        )

    async def handle(
        self,
        *,
        actor: User,
        job_id: UUID,
        correlation_id: str | None,
        filename_stem: str | None = None,
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
        artifact = apply_single_file_protocol_filename(
            artifact=artifact,
            input_filename=job.input_filename,
            output_format=job.output_format,
            created_at=job.created_at,
            filename_stem=filename_stem,
        )
        source_artifact_id = build_document_converter_source_artifact_id(
            upstream_job_id=job.upstream_job_id or ""
        )
        vault_artifact = await self._vault_saves.save(
            actor=actor,
            artifact=artifact,
            source_artifact_id=source_artifact_id,
        )
        return SaveDocumentConverterArtifactResult(
            vault_artifact=vault_artifact,
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
