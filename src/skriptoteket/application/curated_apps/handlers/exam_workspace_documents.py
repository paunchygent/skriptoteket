"""Exam workspace document handlers: DOCX import, reopen, and versioned save.

The native exam document persists as one immutable Mina filer container per
revision (D2/S3). Version numbers advance under the per-user vault usage
lock, with the partial unique index on (user, lineage, version) as the
database backstop; a stale ``expected_revision`` maps to CONFLICT exactly
like the correction-session precedent.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceDocumentListResponse,
    ExamWorkspaceDocumentResponse,
    ExamWorkspaceDocumentSummary,
    SaveExamWorkspaceDocumentRequest,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.input_files import sanitize_input_filename
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind, VaultUsage
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_workspace import (
    DocxExamExtractorProtocol,
    ExamWorkspaceContainerCodecProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)

EXAM_WORKSPACE_SOURCE_ARTIFACT_PREFIX = "documents.conversion_hub:exam-workspace"


def _document_not_found(lineage_id: UUID) -> DomainError:
    return DomainError(
        code=ErrorCode.NOT_FOUND,
        message="Provdokumentet finns inte.",
        details={"lineage_id": str(lineage_id)},
    )


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
                await self._vault_storage.delete_file(user_id=actor.id, file_id=file_id)
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message="Dokumentet sparades samtidigt i en annan flik.",
                details={"lineage_id": str(lineage_id), "version": version},
            ) from error
        except Exception:
            if stored:
                await self._vault_storage.delete_file(user_id=actor.id, file_id=file_id)
            raise
        return vault_file

    async def load_version(self, *, actor: User, vault_file: VaultFile) -> bytes:
        return await self._vault_storage.read_file(user_id=actor.id, file_id=vault_file.id)


def _summary(vault_file: VaultFile) -> ExamWorkspaceDocumentSummary:
    assert vault_file.document_lineage_id is not None
    assert vault_file.document_version is not None
    return ExamWorkspaceDocumentSummary(
        lineage_id=vault_file.document_lineage_id,
        version=vault_file.document_version,
        vault_file_id=vault_file.id,
        name=vault_file.name,
        saved_at=vault_file.created_at,
    )


class ImportExamWorkspaceDocumentHandler:
    """Import one teacher DOCX into a new versioned exam workspace document."""

    def __init__(
        self,
        *,
        extractor: DocxExamExtractorProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._extractor = extractor
        self._codec = codec
        self._store = store
        self._id_generator = id_generator

    async def handle(
        self, *, actor: User, filename: str, content: bytes
    ) -> ExamWorkspaceDocumentResponse:
        safe_name = sanitize_input_filename(input_filename=filename)
        if not safe_name.lower().endswith(".docx"):
            raise validation_error("Välj en .docx-fil.", details={"filename": safe_name})
        if not content:
            raise validation_error("Filen saknar innehåll.")

        document_id = self._id_generator.new_uuid()
        extraction = self._extractor.extract(
            document_id=document_id, filename=safe_name, content=content
        )
        container = ExamWorkspaceContainerContent(
            document=extraction.document, assets_by_id={}, notes=extraction.notes
        )
        container_bytes = self._codec.build(content=container)
        stem = PurePosixPath(safe_name).stem or "prov"
        vault_file = await self._store.save_version(
            actor=actor,
            file_id=self._id_generator.new_uuid(),
            name=f"{stem}.provdokument.zip",
            content=container_bytes,
            lineage_id=document_id,
            version=1,
        )
        return ExamWorkspaceDocumentResponse(
            document=extraction.document,
            summary=_summary(vault_file),
            notes=extraction.notes,
        )


class GetExamWorkspaceDocumentHandler:
    """Reopen the head version of an exam workspace document."""

    def __init__(
        self,
        *,
        vault_files: VaultFileRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
    ) -> None:
        self._vault_files = vault_files
        self._codec = codec
        self._store = store

    async def handle(self, *, actor: User, lineage_id: UUID) -> ExamWorkspaceDocumentResponse:
        head = await self._vault_files.get_document_head(
            user_id=actor.id, document_lineage_id=lineage_id
        )
        if head is None:
            raise _document_not_found(lineage_id)
        content = await self._store.load_version(actor=actor, vault_file=head)
        container = self._codec.parse(content=content)
        if (
            container.document.document_id != lineage_id
            or container.document.revision != head.document_version
        ):
            raise validation_error(
                "Den sparade dokumentversionen är skadad.",
                details={"lineage_id": str(lineage_id)},
            )
        return ExamWorkspaceDocumentResponse(
            document=container.document,
            summary=_summary(head),
            notes=container.notes,
        )


class ListExamWorkspaceDocumentsHandler:
    """List the actor's workspace documents as head-version summaries."""

    def __init__(self, *, vault_files: VaultFileRepositoryProtocol) -> None:
        self._vault_files = vault_files

    async def handle(self, *, actor: User) -> ExamWorkspaceDocumentListResponse:
        heads = await self._vault_files.list_document_heads(
            user_id=actor.id,
            source_artifact_prefix=f"{EXAM_WORKSPACE_SOURCE_ARTIFACT_PREFIX}:",
        )
        return ExamWorkspaceDocumentListResponse(documents=tuple(_summary(head) for head in heads))


class SaveExamWorkspaceDocumentHandler:
    """Save a new document revision guarded by expected_revision (CONFLICT on stale)."""

    def __init__(
        self,
        *,
        vault_files: VaultFileRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._vault_files = vault_files
        self._codec = codec
        self._store = store
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        request: SaveExamWorkspaceDocumentRequest,
    ) -> ExamWorkspaceDocumentResponse:
        head = await self._vault_files.get_document_head(
            user_id=actor.id, document_lineage_id=lineage_id
        )
        if head is None:
            raise _document_not_found(lineage_id)
        if head.document_version != request.expected_revision:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message="Dokumentet har ändrats sedan det öppnades.",
                details={
                    "expected_revision": request.expected_revision,
                    "current_revision": head.document_version,
                },
            )
        document = request.document
        if document.document_id != lineage_id:
            raise validation_error(
                "Dokumentets identitet matchar inte adressen.",
                details={"lineage_id": str(lineage_id)},
            )
        if document.revision != request.expected_revision + 1:
            raise validation_error(
                "Dokumentversionen måste öka med exakt ett vid sparande.",
                details={
                    "expected_revision": request.expected_revision,
                    "document_revision": document.revision,
                },
            )

        assets_by_id: dict[str, bytes] = {}
        if document.assets:
            head_content = await self._store.load_version(actor=actor, vault_file=head)
            head_container = self._codec.parse(content=head_content)
            missing = {
                asset.asset_id
                for asset in document.assets
                if asset.asset_id not in head_container.assets_by_id
            }
            if missing:
                raise validation_error(
                    "Dokumentet hänvisar till bilder som saknas.",
                    details={"missing_assets": sorted(missing)},
                )
            assets_by_id = {
                asset.asset_id: head_container.assets_by_id[asset.asset_id]
                for asset in document.assets
            }

        container_bytes = self._codec.build(
            content=ExamWorkspaceContainerContent(
                document=document, assets_by_id=assets_by_id, notes=()
            )
        )
        vault_file = await self._store.save_version(
            actor=actor,
            file_id=self._id_generator.new_uuid(),
            name=head.name,
            content=container_bytes,
            lineage_id=lineage_id,
            version=document.revision,
        )
        return ExamWorkspaceDocumentResponse(
            document=document, summary=_summary(vault_file), notes=()
        )
