"""Exam workspace document store: versioned container persistence in Mina filer.

The native exam document persists as one immutable Mina filer container per
revision (D2/S3). Version numbers advance under the per-user vault usage
lock, with the partial unique index on (user, lineage, version) as the
database backstop; a duplicate version maps to CONFLICT. Retiring a
superseded revision soft-deletes its row and releases its bytes from vault
usage.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError

from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind, VaultUsage
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)

EXAM_WORKSPACE_SOURCE_ARTIFACT_PREFIX = "documents.conversion_hub:exam-workspace"


class ExamWorkspaceDocumentStore:
    """Persist and load versioned exam workspace containers in Mina filer."""

    def __init__(
        self,
        *,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        settings: Settings,
    ) -> None:
        self._vault_files = vault_files
        self._vault_usage = vault_usage
        self._vault_storage = vault_storage
        self._uow = uow
        self._clock = clock
        self._settings = settings

    async def save_version(
        self,
        *,
        actor: User,
        file_id: UUID,
        name: str,
        content: bytes,
        lineage_id: UUID,
        version: int,
    ) -> VaultFile:
        actual_bytes = len(content)
        if actual_bytes <= 0:
            raise validation_error("Dokumentet saknar innehåll.")
        if actual_bytes > self._settings.VAULT_MAX_FILE_BYTES:
            raise validation_error(
                "Dokumentet är större än maxstorleken för Mina filer.",
                details={
                    "bytes": actual_bytes,
                    "max_bytes": self._settings.VAULT_MAX_FILE_BYTES,
                },
            )

        now = self._clock.now()
        stored = False
        try:
            async with self._uow:
                usage = await self._vault_usage.get_for_update(user_id=actor.id, now=now)
                if usage.bytes_total + actual_bytes > self._settings.VAULT_MAX_TOTAL_BYTES:
                    raise validation_error(
                        "Mina filer är fullt; ta bort filer och försök igen.",
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
                        name=name,
                        bytes=actual_bytes,
                        source_kind=VaultFileSourceKind.APP_EXPORT,
                        source_run_id=None,
                        source_artifact_id=(
                            f"{EXAM_WORKSPACE_SOURCE_ARTIFACT_PREFIX}:{lineage_id}:v{version}"
                        ),
                        document_lineage_id=lineage_id,
                        document_version=version,
                        created_at=now,
                        deleted_at=None,
                    )
                )
                await self._vault_storage.store_file(
                    user_id=actor.id, file_id=vault_file.id, content=content
                )
                stored = True
                await self._vault_usage.upsert(
                    usage=VaultUsage(
                        user_id=actor.id,
                        bytes_total=usage.bytes_total + actual_bytes,
                        updated_at=now,
                    )
                )
        except IntegrityError as error:
            if stored:
                await self.discard_version_file(actor=actor, file_id=file_id)
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message="Dokumentet sparades samtidigt i en annan flik.",
                details={"lineage_id": str(lineage_id), "version": version},
            ) from error
        except Exception:
            if stored:
                await self.discard_version_file(actor=actor, file_id=file_id)
            raise
        return vault_file

    async def retire_version(self, *, actor: User, retired: VaultFile) -> None:
        """Soft-delete one superseded revision and release its bytes from vault usage.

        Runs inside the caller's unit of work; the stored payload expires with the row.
        """
        now = self._clock.now()
        await self._vault_files.update(file=retired.model_copy(update={"deleted_at": now}))
        usage = await self._vault_usage.get_for_update(user_id=actor.id, now=now)
        await self._vault_usage.upsert(
            usage=VaultUsage(
                user_id=actor.id,
                bytes_total=max(0, usage.bytes_total - retired.bytes),
                updated_at=now,
            )
        )

    async def discard_version_file(self, *, actor: User, file_id: UUID) -> None:
        await self._vault_storage.delete_file(user_id=actor.id, file_id=file_id)

    async def load_version(self, *, actor: User, vault_file: VaultFile) -> bytes:
        return await self._vault_storage.read_file(user_id=actor.id, file_id=vault_file.id)
