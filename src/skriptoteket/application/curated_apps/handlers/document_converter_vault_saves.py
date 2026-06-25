"""Document Converter Vault save service.

Purpose:
    Save server-authorized Document Converter artifacts into Mina filer while
    enforcing Vault quotas and preserving app-export source artifact identity.

Relationships:
    Shared by the single-result Document Converter artifact handler and the
    HTML/CSS project preview artifact save handler.
"""

from __future__ import annotations

from skriptoteket.application.curated_apps.conversion_hub_saved_artifacts import (
    ConversionHubSavedVaultArtifact,
)
from skriptoteket.application.curated_apps.document_converter import (
    DocumentConverterStoredArtifact,
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


class DocumentConverterVaultSaveService:
    """Persist one server-owned Document Converter artifact into Vault."""

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

    async def save(
        self,
        *,
        actor: User,
        artifact: DocumentConverterStoredArtifact,
        source_artifact_id: str,
    ) -> ConversionHubSavedVaultArtifact:
        """Save one artifact and return its Vault summary."""
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

        return await self._store(
            actor=actor,
            filename=filename,
            content=content,
            actual_bytes=actual_bytes,
            source_artifact_id=source_artifact_id,
        )

    async def _store(
        self,
        *,
        actor: User,
        filename: str,
        content: bytes,
        actual_bytes: int,
        source_artifact_id: str,
    ) -> ConversionHubSavedVaultArtifact:
        now = self._clock.now()
        file_id = self._id_generator.new_uuid()
        stored = False

        try:
            async with self._uow:
                usage = await self._vault_usage.get_for_update(user_id=actor.id, now=now)
                _validate_quota(
                    usage=usage,
                    actual_bytes=actual_bytes,
                    max_total_bytes=self._settings.VAULT_MAX_TOTAL_BYTES,
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

        return ConversionHubSavedVaultArtifact(
            file_id=vault_file.id,
            name=vault_file.name,
            bytes=vault_file.bytes,
            created_at=vault_file.created_at,
        )


def _validate_quota(
    *,
    usage: VaultUsage,
    actual_bytes: int,
    max_total_bytes: int,
) -> None:
    if usage.bytes_total + actual_bytes > max_total_bytes:
        raise validation_error(
            "Vault quota exceeded.",
            details={
                "bytes_total": usage.bytes_total,
                "attempted_bytes": actual_bytes,
                "max_total_bytes": max_total_bytes,
            },
        )
