from __future__ import annotations

from pathlib import PurePosixPath

from pydantic import ValidationError

from skriptoteket.application.scripting.handlers._vault_helpers import build_vault_file_info
from skriptoteket.application.scripting.vault import SaveVaultFileCommand, SaveVaultFileResult
from skriptoteket.config import Settings
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.domain.scripting.input_files import sanitize_input_filename
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind, VaultUsage
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.runner import ArtifactManagerProtocol
from skriptoteket.protocols.scripting import ToolRunRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    SaveVaultFileHandlerProtocol,
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)


class SaveVaultFileHandler(SaveVaultFileHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        runs: ToolRunRepositoryProtocol,
        artifacts: ArtifactManagerProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        settings: Settings,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._runs = runs
        self._artifacts = artifacts
        self._vault_files = vault_files
        self._vault_usage = vault_usage
        self._vault_storage = vault_storage
        self._settings = settings
        self._clock = clock
        self._id_generator = id_generator

    async def handle(self, *, actor: User, command: SaveVaultFileCommand) -> SaveVaultFileResult:
        if command.source_kind is not VaultFileSourceKind.RUN_ARTIFACT:
            raise validation_error(
                "Unsupported vault source kind.",
                details={"source_kind": command.source_kind.value},
            )

        now = self._clock.now()
        file_id = self._id_generator.new_uuid()
        stored_file = False

        try:
            async with self._uow:
                run = await self._runs.get_by_id(run_id=command.run_id)
                if run is None or run.requested_by_user_id != actor.id:
                    raise not_found("ToolRun", str(command.run_id))

                try:
                    manifest = ArtifactsManifest.model_validate(run.artifacts_manifest)
                except ValidationError as exc:
                    raise validation_error(
                        "Run artifacts manifest is invalid.",
                        details={"run_id": str(run.id)},
                    ) from exc
                artifact = next(
                    (
                        item
                        for item in manifest.artifacts
                        if item.artifact_id == command.artifact_id
                    ),
                    None,
                )
                if artifact is None:
                    raise not_found("Artifact", command.artifact_id)

                if artifact.bytes > self._settings.VAULT_MAX_FILE_BYTES:
                    raise validation_error(
                        "Vault file exceeds the max file size.",
                        details={
                            "bytes": artifact.bytes,
                            "max_bytes": self._settings.VAULT_MAX_FILE_BYTES,
                        },
                    )

                usage = await self._vault_usage.get_for_update(user_id=actor.id, now=now)
                if usage.bytes_total + artifact.bytes > self._settings.VAULT_MAX_TOTAL_BYTES:
                    raise validation_error(
                        "Vault quota exceeded.",
                        details={
                            "bytes_total": usage.bytes_total,
                            "attempted_bytes": artifact.bytes,
                            "max_total_bytes": self._settings.VAULT_MAX_TOTAL_BYTES,
                        },
                    )

                content = self._artifacts.read_artifact(
                    run_id=run.id,
                    artifact_path=artifact.path,
                )
                actual_bytes = len(content)
                if actual_bytes > self._settings.VAULT_MAX_FILE_BYTES:
                    raise validation_error(
                        "Vault file exceeds the max file size.",
                        details={
                            "bytes": actual_bytes,
                            "max_bytes": self._settings.VAULT_MAX_FILE_BYTES,
                        },
                    )
                if usage.bytes_total + actual_bytes > self._settings.VAULT_MAX_TOTAL_BYTES:
                    raise validation_error(
                        "Vault quota exceeded.",
                        details={
                            "bytes_total": usage.bytes_total,
                            "attempted_bytes": actual_bytes,
                            "max_total_bytes": self._settings.VAULT_MAX_TOTAL_BYTES,
                        },
                    )

                if command.name is not None and command.name.strip():
                    name = command.name
                else:
                    name = PurePosixPath(artifact.path).name
                safe_name = sanitize_input_filename(input_filename=name)

                vault_file = VaultFile(
                    id=file_id,
                    user_id=actor.id,
                    name=safe_name,
                    bytes=actual_bytes,
                    source_kind=command.source_kind,
                    source_run_id=run.id,
                    source_artifact_id=artifact.artifact_id,
                    created_at=now,
                    deleted_at=None,
                )

                created = await self._vault_files.create(file=vault_file)
                await self._vault_storage.store_file(
                    user_id=actor.id,
                    file_id=created.id,
                    content=content,
                )
                stored_file = True

                await self._vault_usage.upsert(
                    usage=VaultUsage(
                        user_id=actor.id,
                        bytes_total=usage.bytes_total + actual_bytes,
                        updated_at=now,
                    )
                )

            return SaveVaultFileResult(file=build_vault_file_info(vault_file=created))
        except Exception:
            if stored_file:
                await self._vault_storage.delete_file(
                    user_id=actor.id,
                    file_id=file_id,
                )
            raise
