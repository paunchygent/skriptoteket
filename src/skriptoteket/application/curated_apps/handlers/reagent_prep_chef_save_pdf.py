from __future__ import annotations

from skriptoteket.application.curated_apps.reagent_prep_chef import (
    ReagentPrepChefSavePdfRequest,
    ReagentPrepChefSavePdfResult,
)
from skriptoteket.application.scripting.handlers._vault_helpers import build_vault_file_info
from skriptoteket.config import Settings
from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.input_files import sanitize_input_filename
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind, VaultUsage
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.reagent_prep_chef import (
    ReagentPrepChefExportPdfHandlerProtocol,
    ReagentPrepChefSavePdfHandlerProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)


class ReagentPrepChefSavePdfHandler(ReagentPrepChefSavePdfHandlerProtocol):
    def __init__(
        self,
        *,
        export_pdf: ReagentPrepChefExportPdfHandlerProtocol,
        uow: UnitOfWorkProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        settings: Settings,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._export_pdf = export_pdf
        self._uow = uow
        self._vault_files = vault_files
        self._vault_usage = vault_usage
        self._vault_storage = vault_storage
        self._settings = settings
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self, *, actor: User, command: ReagentPrepChefSavePdfRequest
    ) -> ReagentPrepChefSavePdfResult:
        pdf_bytes = await self._export_pdf.handle(actor=actor, command=command.prep)
        actual_bytes = len(pdf_bytes)

        if actual_bytes > self._settings.VAULT_MAX_FILE_BYTES:
            raise validation_error(
                "Vault file exceeds the max file size.",
                details={
                    "bytes": actual_bytes,
                    "max_bytes": self._settings.VAULT_MAX_FILE_BYTES,
                },
            )

        name = command.name.strip() if command.name else "reagensberedning.pdf"
        safe_name = sanitize_input_filename(input_filename=name)

        now = self._clock.now()
        file_id = self._id_generator.new_uuid()
        stored_file = False

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

                vault_file = VaultFile(
                    id=file_id,
                    user_id=actor.id,
                    name=safe_name,
                    bytes=actual_bytes,
                    source_kind=VaultFileSourceKind.APP_EXPORT,
                    source_run_id=None,
                    source_artifact_id="chemistry.reagent_prep_chef",
                    created_at=now,
                    deleted_at=None,
                )

                created = await self._vault_files.create(file=vault_file)
                await self._vault_storage.store_file(
                    user_id=actor.id,
                    file_id=created.id,
                    content=pdf_bytes,
                )
                stored_file = True

                await self._vault_usage.upsert(
                    usage=VaultUsage(
                        user_id=actor.id,
                        bytes_total=usage.bytes_total + actual_bytes,
                        updated_at=now,
                    )
                )

            return ReagentPrepChefSavePdfResult(file=build_vault_file_info(vault_file=created))
        except Exception:
            if stored_file:
                await self._vault_storage.delete_file(user_id=actor.id, file_id=file_id)
            raise
