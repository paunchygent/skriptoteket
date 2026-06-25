"""Document Converter producer and artifact protocols.

Purpose:
    Keep the route-inactive Document Converter backend contract protocol-first
    while allowing local app-boundary producers and server-owned artifact
    storage to evolve independently of FastAPI and concrete filesystem code.

Relationships:
    Used by ``application.curated_apps.handlers.document_converter_jobs`` and
    implemented by ``application.curated_apps.document_converter_producers``
    plus ``infrastructure.documents.document_converter_artifacts``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from skriptoteket.application.curated_apps.conversion_hub import ConversionHubJobSpecV2
from skriptoteket.application.curated_apps.document_converter import (
    DocumentConverterStoredArtifact,
)
from skriptoteket.application.curated_apps.document_converter_projects import (
    CleanupDocumentConverterProjectPreviewsResult,
    DocumentConverterProjectManifest,
    DocumentConverterProjectPreviewRecord,
    DocumentConverterProjectUploadedFile,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import (
    ConversionHubUpload,
)


class LocalDocumentConverterProducerProtocol(Protocol):
    """Produce one local Document Converter result artifact."""

    async def convert(
        self,
        *,
        spec: ConversionHubJobSpecV2,
        upload: ConversionHubUpload,
        correlation_id: str | None,
    ) -> DocumentConverterStoredArtifact: ...


class DocumentConverterArtifactStoreProtocol(Protocol):
    """Store and read server-owned local Document Converter artifacts."""

    def store_artifact(
        self,
        *,
        job_id: UUID,
        artifact: DocumentConverterStoredArtifact,
    ) -> None: ...

    def read_artifact(self, *, job_id: UUID) -> DocumentConverterStoredArtifact: ...


class DocumentConverterProjectPreviewRendererProtocol(Protocol):
    """Render HTML/CSS project files into temporary PDF preview artifacts."""

    def render_project(
        self,
        *,
        manifest: DocumentConverterProjectManifest,
        files: list[DocumentConverterProjectUploadedFile],
    ) -> list[DocumentConverterStoredArtifact]: ...


class DocumentConverterProjectPreviewStoreProtocol(Protocol):
    """Store and authorize temporary Document Converter project preview artifacts."""

    def store_preview(
        self,
        *,
        record: DocumentConverterProjectPreviewRecord,
        artifacts: list[DocumentConverterStoredArtifact],
    ) -> None: ...

    def get_preview(
        self,
        *,
        owner_user_id: UUID,
        preview_id: UUID,
        now: datetime,
    ) -> DocumentConverterProjectPreviewRecord: ...

    def read_artifact(
        self,
        *,
        owner_user_id: UUID,
        preview_id: UUID,
        artifact_id: UUID,
        now: datetime,
    ) -> DocumentConverterStoredArtifact: ...

    def discard_preview(
        self,
        *,
        owner_user_id: UUID,
        preview_id: UUID,
        now: datetime,
    ) -> DocumentConverterProjectPreviewRecord: ...

    def cleanup_expired(
        self,
        *,
        now: datetime,
    ) -> CleanupDocumentConverterProjectPreviewsResult: ...
