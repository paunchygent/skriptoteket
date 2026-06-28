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

from dataclasses import dataclass
from uuid import UUID

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJobSpecV2,
    ConversionHubSourceFormatV2,
)
from skriptoteket.application.curated_apps.document_converter import (
    DocumentConverterSavedFileOption,
    DocumentConverterSubmitResult,
    ListDocumentConverterSavedFilesResult,
    infer_document_converter_source_format,
    validate_document_converter_batch_count,
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
    """Submit owner-scoped Mina filer sources through the job flow."""

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
        source_refs: list[str],
        wait_seconds: int,
        correlation_id: str | None,
        build_job_spec: JobSpecBuilder,
    ) -> DocumentConverterSubmitResult:
        saved_files = await self._load_authorized_saved_files(
            actor=actor,
            source_refs=source_refs,
            expected_source_format=spec.source_format,
        )
        uploads: list[ConversionHubUpload] = []
        for saved_file in saved_files:
            file_bytes = await self._vault_storage.read_file(
                user_id=actor.id,
                file_id=saved_file.file.id,
            )
            uploads.append(
                ConversionHubUpload(
                    filename=saved_file.file.name,
                    content_type=saved_file.content_type,
                    file_bytes=file_bytes,
                )
            )
        return await self._create_jobs.handle(
            actor=actor,
            spec=spec,
            uploads=uploads,
            wait_seconds=wait_seconds,
            correlation_id=correlation_id,
            build_job_spec=build_job_spec,
        )

    async def _load_authorized_saved_files(
        self,
        *,
        actor: User,
        source_refs: list[str],
        expected_source_format: ConversionHubSourceFormatV2,
    ) -> list["_SavedFileSource"]:
        validate_document_converter_batch_count(files_count=len(source_refs))
        parsed_refs = [self._parse_vault_ref(source_ref=source_ref) for source_ref in source_refs]
        if len(set(parsed_refs)) != len(parsed_refs):
            raise validation_error("Välj varje sparad fil högst en gång.")

        loaded_files: list[VaultFile] = []
        for raw_value in parsed_refs:
            async with self._uow:
                vault_file = await self._vault_files.get_by_id(file_id=UUID(raw_value))
            if (
                vault_file is None
                or vault_file.user_id != actor.id
                or vault_file.deleted_at is not None
            ):
                raise not_found("VaultFile", raw_value)
            loaded_files.append(vault_file)

        sources: list[_SavedFileSource] = []
        source_formats = set()
        for vault_file in loaded_files:
            if not await self._vault_storage.exists_file(user_id=actor.id, file_id=vault_file.id):
                raise not_found("VaultFile", str(vault_file.id))
            inferred = infer_document_converter_source_format(filename=vault_file.name)
            if inferred is None:
                raise validation_error("Filen kan inte användas i Dokumentkonverteraren.")
            source_format, content_type = inferred
            source_formats.add(source_format)
            sources.append(_SavedFileSource(file=vault_file, content_type=content_type))

        if len(source_formats) > 1:
            raise validation_error("Välj filer med samma källformat.")
        actual_source_format = next(iter(source_formats))
        if actual_source_format is not expected_source_format:
            raise validation_error(
                "De sparade filerna matchar inte valt källformat.",
                details={
                    "expected_source_format": expected_source_format.value,
                    "actual_source_format": actual_source_format.value,
                },
            )
        return sources

    def _parse_vault_ref(self, *, source_ref: str) -> str:
        source, raw_value = parse_file_ref(value=source_ref)
        if source is not FileRefSource.VAULT:
            raise validation_error("Document Converter saved-file sources must use vault refs.")
        return raw_value


@dataclass(frozen=True)
class _SavedFileSource:
    file: VaultFile
    content_type: str
