"""Conversion Hub artifact save handlers.

Purpose:
  Persist authenticated Exam Converter artifacts as owner-scoped Vault app
  exports after the browser has downloaded a named Sir Convert artifact through
  the HuleEdu Gateway.

Relationships:
  - Mirrors Klassrumskartan's app-export Vault finalizer shape for quota,
    storage rollback, and owner-scoped file records.
  - Consumes `conversion_hub_saved_artifacts` commands from the web boundary.
"""

from hashlib import sha256

from skriptoteket.application.curated_apps.conversion_hub_saved_artifacts import (
    ConversionHubSavedVaultArtifact,
    SaveConversionHubSirConvertArtifactCommand,
    SaveConversionHubSirConvertArtifactResult,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.input_files import sanitize_input_filename
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind, VaultUsage
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)

APP_ID = "documents.conversion_hub"


class SaveConversionHubSirConvertArtifactHandler:
    """Save one authenticated Sir Convert artifact into the user's Vault."""

    def __init__(
        self,
        *,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        settings: Settings,
    ) -> None:
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
        command: SaveConversionHubSirConvertArtifactCommand,
    ) -> SaveConversionHubSirConvertArtifactResult:
        actual_bytes = len(command.content)
        self._validate_content(command=command, actual_bytes=actual_bytes)

        now = self._clock.now()
        file_id = self._id_generator.new_uuid()
        source_artifact_id = _build_source_artifact_id(command)
        safe_name = sanitize_input_filename(
            input_filename=command.metadata.saved_display_filename or command.filename
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
                        name=safe_name,
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
                    content=command.content,
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

        return SaveConversionHubSirConvertArtifactResult(
            vault_artifact=ConversionHubSavedVaultArtifact(
                file_id=vault_file.id,
                name=vault_file.name,
                bytes=vault_file.bytes,
                created_at=vault_file.created_at,
            ),
            source_artifact_id=source_artifact_id,
        )

    def _validate_content(
        self,
        *,
        command: SaveConversionHubSirConvertArtifactCommand,
        actual_bytes: int,
    ) -> None:
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
        if command.metadata.size_bytes is not None and command.metadata.size_bytes != actual_bytes:
            raise validation_error(
                "Filens storlek matchar inte konverteringsresultatet.",
                details={
                    "expected_bytes": command.metadata.size_bytes,
                    "actual_bytes": actual_bytes,
                },
            )
        if command.metadata.sha256 is not None:
            actual_hash = sha256(command.content).hexdigest()
            if command.metadata.sha256.lower() != actual_hash:
                raise validation_error("Filen matchar inte konverteringsresultatet.")


def _build_source_artifact_id(command: SaveConversionHubSirConvertArtifactCommand) -> str:
    metadata = command.metadata
    source = f"{APP_ID}:{metadata.sir_convert_job_id}:{metadata.artifact_key}"
    if len(source) <= 255:
        return source
    return f"{APP_ID}:sir-convert:{sha256(source.encode('utf-8')).hexdigest()}"
