"""Document Converter saved-file source handlers.

Purpose:
    Bridge owner-scoped Mina filer records into the existing Document
    Converter single-file job flow without making the browser re-upload saved
    bytes.

Relationships:
    Uses Vault repositories/storage for ownership and file reads, then hands a
    server-built `ConversionHubUpload` to `CreateDocumentConverterJobsHandler`.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.application.curated_apps.conversion_hub import ConversionHubJobSpecV2
from skriptoteket.application.curated_apps.document_converter import (
    DocumentConverterSavedFileOption,
    DocumentConverterSubmitResult,
    ListDocumentConverterSavedFilesResult,
    infer_document_converter_source_format,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import (
    ConversionHubUpload,
    JobSpecBuilder,
)
from skriptoteket.application.curated_apps.handlers.document_converter_jobs import (
    CreateDocumentConverterJobsHandler,
)
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.file_refs import (
    FileRefSource,
    build_vault_file_ref,
    parse_file_ref,
)
from skriptoteket.domain.scripting.vault import VaultFile
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
)


class ListDocumentConverterSavedFilesHandler:
    """List owner-scoped compatible Mina filer sources."""

    def __init__(
        self,
        *,
        vault_files: VaultFileRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        uow: UnitOfWorkProtocol,
    ) -> None:
        self._vault_files = vault_files
        self._vault_storage = vault_storage
        self._uow = uow

    async def handle(self, *, actor: User) -> ListDocumentConverterSavedFilesResult:
        async with self._uow:
            files = await self._vault_files.list_active_for_user(user_id=actor.id)

        compatible_files: list[DocumentConverterSavedFileOption] = []
        for vault_file in files:
            inferred = infer_document_converter_source_format(filename=vault_file.name)
            if inferred is None:
                continue
            if not await self._vault_storage.exists_file(user_id=actor.id, file_id=vault_file.id):
                continue
            compatible_files.append(
                DocumentConverterSavedFileOption(
                    file_id=vault_file.id,
                    ref=build_vault_file_ref(file_id=vault_file.id),
                    name=vault_file.name,
                    bytes=vault_file.bytes,
                    source_format=inferred[0],
                    created_at=vault_file.created_at,
                )
            )

        return ListDocumentConverterSavedFilesResult(files=compatible_files)


class SubmitDocumentConverterSavedFileHandler:
    """Submit one owner-scoped Mina filer source through the job flow."""

    def __init__(
        self,
        *,
        create_jobs: CreateDocumentConverterJobsHandler,
        vault_files: VaultFileRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        uow: UnitOfWorkProtocol,
    ) -> None:
        self._create_jobs = create_jobs
        self._vault_files = vault_files
        self._vault_storage = vault_storage
        self._uow = uow

    async def handle(
        self,
        *,
        actor: User,
        spec: ConversionHubJobSpecV2,
        source_ref: str,
        wait_seconds: int,
        correlation_id: str | None,
        build_job_spec: JobSpecBuilder,
    ) -> DocumentConverterSubmitResult:
        vault_file = await self._load_authorized_saved_file(actor=actor, source_ref=source_ref)
        inferred = infer_document_converter_source_format(filename=vault_file.name)
        if inferred is None:
            raise validation_error("Filen kan inte användas i Dokumentkonverteraren.")
        source_format, content_type = inferred
        if source_format is not spec.source_format:
            raise validation_error(
                "Den sparade filen matchar inte valt källformat.",
                details={
                    "expected_source_format": spec.source_format.value,
                    "actual_source_format": source_format.value,
                    "filename": vault_file.name,
                },
            )

        file_bytes = await self._vault_storage.read_file(
            user_id=actor.id,
            file_id=vault_file.id,
        )
        return await self._create_jobs.handle(
            actor=actor,
            spec=spec,
            uploads=[
                ConversionHubUpload(
                    filename=vault_file.name,
                    content_type=content_type,
                    file_bytes=file_bytes,
                )
            ],
            wait_seconds=wait_seconds,
            correlation_id=correlation_id,
            build_job_spec=build_job_spec,
        )

    async def _load_authorized_saved_file(self, *, actor: User, source_ref: str) -> VaultFile:
        source, raw_value = parse_file_ref(value=source_ref)
        if source is not FileRefSource.VAULT:
            raise validation_error("Document Converter saved-file sources must use vault refs.")

        file_id = UUID(raw_value)
        async with self._uow:
            vault_file = await self._vault_files.get_by_id(file_id=file_id)

        if (
            vault_file is None
            or vault_file.user_id != actor.id
            or vault_file.deleted_at is not None
        ):
            raise not_found("VaultFile", raw_value)
        if not await self._vault_storage.exists_file(user_id=actor.id, file_id=vault_file.id):
            raise not_found("VaultFile", raw_value)
        return vault_file
