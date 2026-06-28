"""Document Converter HTML/CSS project preview handlers.

Purpose:
    Render, inspect, discard, clean up, download, and explicitly save temporary
    HTML/CSS project preview PDFs under server-owned preview artifact authority.

Relationships:
    Uses the project manifest contracts, renderer/store protocols, Clock and ID
    services, and shared Vault save service while keeping FastAPI and
    filesystem details outside the application layer.
"""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from skriptoteket.application.curated_apps.document_converter import (
    DocumentConverterStoredArtifact,
)
from skriptoteket.application.curated_apps.document_converter_artifact_hygiene import (
    validate_document_converter_teacher_artifact,
)
from skriptoteket.application.curated_apps.document_converter_file_naming import (
    apply_project_preview_protocol_filenames,
    build_project_preview_filename_from_stem,
)
from skriptoteket.application.curated_apps.document_converter_projects import (
    DOCUMENT_CONVERTER_PROJECT_PREVIEW_TTL_SECONDS,
    CleanupDocumentConverterProjectPreviewsResult,
    DiscardDocumentConverterProjectPreviewResult,
    DocumentConverterProjectManifest,
    DocumentConverterProjectOutputMode,
    DocumentConverterProjectPreviewArtifact,
    DocumentConverterProjectPreviewArtifactKind,
    DocumentConverterProjectPreviewRecord,
    DocumentConverterProjectPreviewResult,
    DocumentConverterProjectPreviewStatus,
    DocumentConverterProjectUploadedFile,
    SaveDocumentConverterProjectPreviewArtifactResult,
    build_document_converter_project_preview_source_artifact_id,
)
from skriptoteket.application.curated_apps.handlers.document_converter_vault_saves import (
    DocumentConverterVaultSaveService,
)
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.document_converter import (
    DocumentConverterProjectPreviewRendererProtocol,
    DocumentConverterProjectPreviewStoreProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)


class RenderDocumentConverterProjectPreviewHandler:
    """Render and store one temporary HTML/CSS project preview."""

    def __init__(
        self,
        *,
        renderer: DocumentConverterProjectPreviewRendererProtocol,
        previews: DocumentConverterProjectPreviewStoreProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._renderer = renderer
        self._previews = previews
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        manifest: DocumentConverterProjectManifest,
        files: list[DocumentConverterProjectUploadedFile],
    ) -> DocumentConverterProjectPreviewResult:
        """Render, store, and return a server-authorized preview record."""
        manifest.validate_uploaded_file_set(
            uploaded_filenames={project_file.filename for project_file in files}
        )
        artifacts = self._renderer.render_project(manifest=manifest, files=files)
        now = self._clock.now()
        artifacts = apply_project_preview_protocol_filenames(
            manifest=manifest,
            artifacts=artifacts,
            created_at=now,
        )
        record = DocumentConverterProjectPreviewRecord(
            preview_id=self._id_generator.new_uuid(),
            owner_user_id=actor.id,
            status=DocumentConverterProjectPreviewStatus.SUCCEEDED,
            output_mode=manifest.output_mode,
            created_at=now,
            expires_at=now + timedelta(seconds=DOCUMENT_CONVERTER_PROJECT_PREVIEW_TTL_SECONDS),
            artifacts=_build_artifact_metadata(
                manifest=manifest,
                artifacts=artifacts,
                new_uuid=self._id_generator.new_uuid,
            ),
            template_id=manifest.pdf_controls.template_id,
            error=None,
        )
        self._previews.store_preview(record=record, artifacts=artifacts)
        return _to_preview_result(record)


class GetDocumentConverterProjectPreviewHandler:
    """Load one owner-scoped temporary project preview status."""

    def __init__(
        self,
        *,
        previews: DocumentConverterProjectPreviewStoreProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._previews = previews
        self._clock = clock

    async def handle(
        self,
        *,
        actor: User,
        preview_id: UUID,
    ) -> DocumentConverterProjectPreviewResult:
        """Return preview status and artifact metadata for the owner."""
        record = self._previews.get_preview(
            owner_user_id=actor.id,
            preview_id=preview_id,
            now=self._clock.now(),
        )
        return _to_preview_result(record)


class DownloadDocumentConverterProjectPreviewArtifactHandler:
    """Authorize and return one temporary project preview artifact."""

    def __init__(
        self,
        *,
        previews: DocumentConverterProjectPreviewStoreProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._previews = previews
        self._clock = clock

    async def handle(
        self,
        *,
        actor: User,
        preview_id: UUID,
        artifact_id: UUID,
        filename_stem: str | None = None,
    ) -> DocumentConverterStoredArtifact:
        """Return the server-stored preview artifact for the owner."""
        artifact = self._previews.read_artifact(
            owner_user_id=actor.id,
            preview_id=preview_id,
            artifact_id=artifact_id,
            now=self._clock.now(),
        )
        _validate_preview_teacher_artifact(
            artifact=artifact,
            preview_id=preview_id,
            artifact_id=artifact_id,
        )
        if filename_stem is None:
            return artifact
        return artifact.model_copy(
            update={
                "filename": build_project_preview_filename_from_stem(filename_stem=filename_stem)
            }
        )


class SaveDocumentConverterProjectPreviewArtifactHandler:
    """Save one explicit project preview artifact to Mina filer."""

    def __init__(
        self,
        *,
        previews: DocumentConverterProjectPreviewStoreProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        settings: Settings,
    ) -> None:
        self._previews = previews
        self._clock = clock
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
        preview_id: UUID,
        artifact_id: UUID,
        filename_stem: str | None = None,
    ) -> SaveDocumentConverterProjectPreviewArtifactResult:
        """Save the selected preview artifact through server-owned authority."""
        artifact = self._previews.read_artifact(
            owner_user_id=actor.id,
            preview_id=preview_id,
            artifact_id=artifact_id,
            now=self._clock.now(),
        )
        _validate_preview_teacher_artifact(
            artifact=artifact,
            preview_id=preview_id,
            artifact_id=artifact_id,
        )
        if filename_stem is not None:
            artifact = artifact.model_copy(
                update={
                    "filename": build_project_preview_filename_from_stem(
                        filename_stem=filename_stem
                    )
                }
            )
        source_artifact_id = build_document_converter_project_preview_source_artifact_id(
            preview_id=preview_id,
            artifact_id=artifact_id,
        )
        vault_artifact = await self._vault_saves.save(
            actor=actor,
            artifact=artifact,
            source_artifact_id=source_artifact_id,
        )
        return SaveDocumentConverterProjectPreviewArtifactResult(
            vault_artifact=vault_artifact,
            source_artifact_id=source_artifact_id,
        )


class DiscardDocumentConverterProjectPreviewHandler:
    """Discard one owner-scoped temporary project preview."""

    def __init__(
        self,
        *,
        previews: DocumentConverterProjectPreviewStoreProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._previews = previews
        self._clock = clock

    async def handle(
        self,
        *,
        actor: User,
        preview_id: UUID,
    ) -> DiscardDocumentConverterProjectPreviewResult:
        """Discard the preview and remove its artifact authority."""
        record = self._previews.discard_preview(
            owner_user_id=actor.id,
            preview_id=preview_id,
            now=self._clock.now(),
        )
        return DiscardDocumentConverterProjectPreviewResult(
            preview_id=record.preview_id,
            status=record.status,
        )


class CleanupDocumentConverterProjectPreviewsHandler:
    """Delete expired temporary project preview artifacts."""

    def __init__(
        self,
        *,
        previews: DocumentConverterProjectPreviewStoreProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._previews = previews
        self._clock = clock

    async def handle(self) -> CleanupDocumentConverterProjectPreviewsResult:
        """Remove previews that have passed their target TTL."""
        return self._previews.cleanup_expired(now=self._clock.now())


def _build_artifact_metadata(
    *,
    manifest: DocumentConverterProjectManifest,
    artifacts: list[DocumentConverterStoredArtifact],
    new_uuid,
) -> list[DocumentConverterProjectPreviewArtifact]:
    expected_kinds = _artifact_kinds(manifest=manifest)
    return [
        DocumentConverterProjectPreviewArtifact(
            artifact_id=new_uuid(),
            kind=kind,
            filename=artifact.filename,
            content_type=artifact.content_type,
            size_bytes=len(artifact.content),
            source_entry_id=entry_id,
            download_url=None,
        )
        for artifact, (kind, entry_id) in zip(artifacts, expected_kinds, strict=True)
    ]


def _artifact_kinds(
    *,
    manifest: DocumentConverterProjectManifest,
) -> list[tuple[DocumentConverterProjectPreviewArtifactKind, str | None]]:
    kinds: list[tuple[DocumentConverterProjectPreviewArtifactKind, str | None]] = []
    if manifest.output_mode in {
        DocumentConverterProjectOutputMode.SEPARATE_PDFS,
        DocumentConverterProjectOutputMode.BOTH,
    }:
        kinds.extend(
            (DocumentConverterProjectPreviewArtifactKind.SEPARATE_PDF, entry.entry_id)
            for entry in manifest.html_entries
        )
    if manifest.output_mode in {
        DocumentConverterProjectOutputMode.COMBINED_PDF,
        DocumentConverterProjectOutputMode.BOTH,
    }:
        kinds.append((DocumentConverterProjectPreviewArtifactKind.COMBINED_PDF, None))
    return kinds


def _validate_preview_teacher_artifact(
    *,
    artifact: DocumentConverterStoredArtifact,
    preview_id: UUID,
    artifact_id: UUID,
) -> None:
    source_artifact_id = build_document_converter_project_preview_source_artifact_id(
        preview_id=preview_id,
        artifact_id=artifact_id,
    )
    validate_document_converter_teacher_artifact(
        artifact=artifact,
        source_artifact_id=source_artifact_id,
        additional_internal_markers=(str(preview_id), str(artifact_id)),
    )


def _to_preview_result(
    record: DocumentConverterProjectPreviewRecord,
) -> DocumentConverterProjectPreviewResult:
    return DocumentConverterProjectPreviewResult(
        preview_id=record.preview_id,
        status=record.status,
        output_mode=record.output_mode,
        created_at=record.created_at,
        expires_at=record.expires_at,
        artifacts=record.artifacts,
        template_id=record.template_id,
        error=record.error,
    )
