"""Conversion Hub transcript formatter artifact action handlers.

Domain purpose:
  Authorize overlay-aware transcript formatter artifact downloads and Mina filer
  saves from persisted replay artifact references only.

Relationships:
  - Consumes PR-0347 replay provenance persisted through
    `ConversionHubTranscriptFormatterArtifactRepositoryProtocol`.
  - Retrieves producer bytes through `SirConvertALotClientV2Protocol` named
    artifact downloads instead of formatting transcript content locally.
  - Reuses Vault app-export persistence for user-owned Mina filer saves.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Protocol
from uuid import UUID

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubJobStatus,
    ConversionHubOutputFormatV2,
    ConversionHubSourceFormatV2,
)
from skriptoteket.application.curated_apps.conversion_hub_saved_artifacts import (
    ConversionHubSavedVaultArtifact,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_artifact_actions import (
    ConversionHubTranscriptFormatterArtifactDownload,
    ConversionHubTranscriptFormatterArtifactRecord,
    SaveConversionHubTranscriptFormatterArtifactResult,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_replay import (
    ConversionHubTranscriptFormatterArtifactKey,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_saves import (
    ConversionHubSavedTranscript,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.input_files import sanitize_input_filename
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind, VaultUsage
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.conversion_hub import (
    ConversionHubJobRepositoryProtocol,
    ConversionHubSavedTranscriptRepositoryProtocol,
    ConversionHubTranscriptFormatterArtifactRepositoryProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.sir_convert_a_lot_v2 import (
    SirConvertArtifactOutcomeV2,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)

APP_ID = "documents.conversion_hub"

_EXTENSION_BY_ARTIFACT_KEY = {
    ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_TXT: "txt",
    ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_MD: "md",
    ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_VTT: "vtt",
    ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_SRT: "srt",
}


class _NamedArtifactClientProtocol(Protocol):
    async def download_named_artifact(
        self,
        job_id: str,
        artifact_key: str,
        *,
        correlation_id: str | None,
    ) -> SirConvertArtifactOutcomeV2: ...


class _AuthorizedFormatterArtifact:
    def __init__(
        self,
        *,
        transcript: ConversionHubSavedTranscript,
        record: ConversionHubTranscriptFormatterArtifactRecord,
        job: ConversionHubJob,
    ) -> None:
        self.transcript = transcript
        self.record = record
        self.job = job


class _FormatterArtifactActionBase:
    def __init__(
        self,
        *,
        jobs: ConversionHubJobRepositoryProtocol,
        transcripts: ConversionHubSavedTranscriptRepositoryProtocol,
        artifacts: ConversionHubTranscriptFormatterArtifactRepositoryProtocol,
        client: _NamedArtifactClientProtocol,
        uow: UnitOfWorkProtocol,
    ) -> None:
        self._jobs = jobs
        self._transcripts = transcripts
        self._artifacts = artifacts
        self._client = client
        self._uow = uow

    async def _download_authorized_artifact(
        self,
        *,
        actor: User,
        transcript_id: UUID,
        artifact_key: ConversionHubTranscriptFormatterArtifactKey,
        correlation_id: str | None,
    ) -> tuple[_AuthorizedFormatterArtifact, bytes]:
        authorized = await self._load_authorized_artifact(
            actor=actor,
            transcript_id=transcript_id,
            artifact_key=artifact_key,
        )
        outcome = await self._client.download_named_artifact(
            authorized.record.sir_convert_job_id,
            authorized.record.artifact_key.value,
            correlation_id=correlation_id,
        )
        content = outcome.artifact.content
        _validate_downloaded_artifact(
            record=authorized.record,
            content_type=outcome.artifact.content_type,
            content=content,
        )
        return authorized, content

    async def _load_authorized_artifact(
        self,
        *,
        actor: User,
        transcript_id: UUID,
        artifact_key: ConversionHubTranscriptFormatterArtifactKey,
    ) -> _AuthorizedFormatterArtifact:
        async with self._uow:
            transcript = await self._transcripts.get_by_owner_and_id(
                owner_user_id=actor.id,
                transcript_id=transcript_id,
            )
            record = await self._artifacts.get_by_owner_transcript_and_key(
                owner_user_id=actor.id,
                transcript_id=transcript_id,
                artifact_key=artifact_key,
            )
            job = (
                await self._jobs.get_by_id(job_id=record.conversion_hub_job_id) if record else None
            )
        if transcript is None or record is None or job is None:
            raise not_found("ConversionHubTranscriptFormatterArtifact", str(transcript_id))
        _validate_replay_provenance(transcript=transcript, record=record, job=job)
        return _AuthorizedFormatterArtifact(transcript=transcript, record=record, job=job)


class DownloadConversionHubTranscriptFormatterArtifactHandler(_FormatterArtifactActionBase):
    """Download one authorized producer formatter artifact."""

    async def handle(
        self,
        *,
        actor: User,
        transcript_id: UUID,
        artifact_key: ConversionHubTranscriptFormatterArtifactKey,
        correlation_id: str | None,
    ) -> ConversionHubTranscriptFormatterArtifactDownload:
        authorized, content = await self._download_authorized_artifact(
            actor=actor,
            transcript_id=transcript_id,
            artifact_key=artifact_key,
            correlation_id=correlation_id,
        )
        return ConversionHubTranscriptFormatterArtifactDownload(
            filename=_product_filename(
                transcript_id=authorized.transcript.id,
                artifact_key=artifact_key,
            ),
            content_type=authorized.record.content_type,
            content=content,
        )


class SaveConversionHubTranscriptFormatterArtifactHandler(_FormatterArtifactActionBase):
    """Save one authorized producer formatter artifact as a Vault app export."""

    def __init__(
        self,
        *,
        jobs: ConversionHubJobRepositoryProtocol,
        transcripts: ConversionHubSavedTranscriptRepositoryProtocol,
        artifacts: ConversionHubTranscriptFormatterArtifactRepositoryProtocol,
        client: _NamedArtifactClientProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        settings: Settings,
    ) -> None:
        super().__init__(
            jobs=jobs,
            transcripts=transcripts,
            artifacts=artifacts,
            client=client,
            uow=uow,
        )
        self._vault_files = vault_files
        self._vault_usage = vault_usage
        self._vault_storage = vault_storage
        self._clock = clock
        self._id_generator = id_generator
        self._settings = settings

    async def handle(
        self,
        *,
        actor: User,
        transcript_id: UUID,
        artifact_key: ConversionHubTranscriptFormatterArtifactKey,
        correlation_id: str | None,
    ) -> SaveConversionHubTranscriptFormatterArtifactResult:
        authorized, content = await self._download_authorized_artifact(
            actor=actor,
            transcript_id=transcript_id,
            artifact_key=artifact_key,
            correlation_id=correlation_id,
        )
        return await self._save_artifact(actor=actor, authorized=authorized, content=content)

    async def _save_artifact(
        self,
        *,
        actor: User,
        authorized: _AuthorizedFormatterArtifact,
        content: bytes,
    ) -> SaveConversionHubTranscriptFormatterArtifactResult:
        actual_bytes = len(content)
        _validate_vault_size(actual_bytes=actual_bytes, settings=self._settings)
        now = self._clock.now()
        file_id = self._id_generator.new_uuid()
        filename = sanitize_input_filename(
            input_filename=_product_filename(
                transcript_id=authorized.transcript.id,
                artifact_key=authorized.record.artifact_key,
            )
        )
        source_artifact_id = _source_artifact_id(authorized)
        vault_file: VaultFile | None = None
        stored = False
        try:
            async with self._uow:
                usage = await self._vault_usage.get_for_update(user_id=actor.id, now=now)
                _validate_vault_quota(
                    usage=usage,
                    actual_bytes=actual_bytes,
                    settings=self._settings,
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
        if vault_file is None:
            raise validation_error("Kunde inte spara filen.")
        return SaveConversionHubTranscriptFormatterArtifactResult(
            vault_artifact=ConversionHubSavedVaultArtifact(
                file_id=vault_file.id,
                name=vault_file.name,
                bytes=vault_file.bytes,
                created_at=vault_file.created_at,
            ),
            source_artifact_id=source_artifact_id,
        )


def _validate_replay_provenance(
    *,
    transcript: ConversionHubSavedTranscript,
    record: ConversionHubTranscriptFormatterArtifactRecord,
    job: ConversionHubJob,
) -> None:
    if job.owner_user_id != transcript.owner_user_id:
        raise not_found("ConversionHubJob", str(record.conversion_hub_job_id))
    if job.upstream_job_id != record.sir_convert_job_id:
        raise validation_error("Replay artifact provenance does not match the replay job.")
    if job.input_filename != _gateway_filename(transcript_id=transcript.id):
        raise validation_error("Replay artifact provenance does not match the saved transcript.")
    if (
        job.source_format is not ConversionHubSourceFormatV2.TRANSCRIPT_JSON
        or job.output_format is not ConversionHubOutputFormatV2.TRANSCRIPT_BUNDLE
        or job.status is not ConversionHubJobStatus.SUCCEEDED
    ):
        raise validation_error("Replay job provenance does not match transcript exports.")
    if record.retrieval_path != _retrieval_path(record=record):
        raise validation_error("Replay artifact reference is not downloadable.")


def _validate_downloaded_artifact(
    *,
    record: ConversionHubTranscriptFormatterArtifactRecord,
    content_type: str,
    content: bytes,
) -> None:
    if len(content) != record.size_bytes:
        raise validation_error("Filen matchar inte konverteringsresultatet.")
    if _content_type_base(content_type) != _content_type_base(record.content_type):
        raise validation_error("Filen matchar inte konverteringsresultatet.")
    if sha256(content).hexdigest() != _plain_sha256(record.sha256):
        raise validation_error("Filen matchar inte konverteringsresultatet.")


def _validate_vault_size(*, actual_bytes: int, settings: Settings) -> None:
    if actual_bytes <= 0:
        raise validation_error("Filen saknar innehåll.")
    if actual_bytes > settings.VAULT_MAX_FILE_BYTES:
        raise validation_error(
            "Vault file exceeds the max file size.",
            details={
                "bytes": actual_bytes,
                "max_bytes": settings.VAULT_MAX_FILE_BYTES,
            },
        )


def _validate_vault_quota(
    *,
    usage: VaultUsage,
    actual_bytes: int,
    settings: Settings,
) -> None:
    if usage.bytes_total + actual_bytes > settings.VAULT_MAX_TOTAL_BYTES:
        raise validation_error(
            "Vault quota exceeded.",
            details={
                "bytes_total": usage.bytes_total,
                "attempted_bytes": actual_bytes,
                "max_total_bytes": settings.VAULT_MAX_TOTAL_BYTES,
            },
        )


def _product_filename(
    *,
    transcript_id: UUID,
    artifact_key: ConversionHubTranscriptFormatterArtifactKey,
) -> str:
    return f"transkript-{transcript_id.hex[:8]}.{_EXTENSION_BY_ARTIFACT_KEY[artifact_key]}"


def _source_artifact_id(authorized: _AuthorizedFormatterArtifact) -> str:
    source = (
        f"{APP_ID}:transcript-replay:"
        f"{authorized.record.conversion_hub_job_id}:{authorized.record.artifact_key.value}"
    )
    if len(source) <= 255:
        return source
    return f"{APP_ID}:transcript-replay:{sha256(source.encode('utf-8')).hexdigest()}"


def _retrieval_path(*, record: ConversionHubTranscriptFormatterArtifactRecord) -> str:
    return f"/v2/convert/jobs/{record.sir_convert_job_id}/artifacts/{record.artifact_key.value}"


def _gateway_filename(*, transcript_id: UUID) -> str:
    return f"saved-transcript-{transcript_id}.json"


def _plain_sha256(value: str) -> str:
    return value.removeprefix("sha256:").lower()


def _content_type_base(value: str) -> str:
    return value.split(";", maxsplit=1)[0].strip().lower()
