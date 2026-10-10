"""Protocol seams for the native exam workspace (ST-SKRIPT-39-04)."""

from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceConversionStatus,
    ExamWorkspaceDocumentListResponse,
    ExamWorkspaceDocumentResponse,
    ExamWorkspaceExportFile,
    ExamWorkspaceExportTarget,
    SaveExamWorkspaceDocumentRequest,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.identity.models import User

if TYPE_CHECKING:
    from skriptoteket.application.curated_apps.handlers.exam_workspace_enrichment import (
        ExamWorkspaceEnrichmentStatusResponse,
    )


class DocxExamChunkerProtocol(Protocol):
    """Segment ordered source text without interpreting exam items."""

    def chunk(self, *, content: bytes) -> tuple[DocxChunk, ...]: ...


class ExamWorkspaceContainerCodecProtocol(Protocol):
    """Fail-closed (de)serialization of versioned exam workspace containers."""

    def build(self, *, content: ExamWorkspaceContainerContent) -> bytes: ...

    def parse(self, *, content: bytes) -> ExamWorkspaceContainerContent: ...


class ExamWorkspaceDocxWriterProtocol(Protocol):
    """Minimal validated DOCX writer for native exam documents (D3)."""

    def build_docx_bytes(self, document: "NativeExamDocument") -> bytes: ...

    def validate_docx_bytes(self, content: bytes, *, expected_item_count: int) -> None: ...


class ListExamWorkspaceDocumentsHandlerProtocol(Protocol):
    async def handle(self, *, actor: User) -> ExamWorkspaceDocumentListResponse: ...


class ImportExamWorkspaceDocumentHandlerProtocol(Protocol):
    async def handle(
        self, *, actor: User, filename: str, content: bytes
    ) -> ExamWorkspaceConversionStatus: ...


class GetExamWorkspaceConversionStatusHandlerProtocol(Protocol):
    async def handle(self, *, actor: User, job_id: UUID) -> ExamWorkspaceConversionStatus: ...


class GetExamWorkspaceDocumentHandlerProtocol(Protocol):
    async def handle(self, *, actor: User, lineage_id: UUID) -> ExamWorkspaceDocumentResponse: ...


class SaveExamWorkspaceDocumentHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        request: SaveExamWorkspaceDocumentRequest,
    ) -> ExamWorkspaceDocumentResponse: ...


class ExportExamWorkspaceDocumentHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        target: ExamWorkspaceExportTarget,
    ) -> ExamWorkspaceExportFile: ...


class EnqueueExamWorkspaceEnrichmentHandlerProtocol(Protocol):
    async def handle(self, *, actor: User, document: NativeExamDocument) -> bool: ...


class GetExamWorkspaceEnrichmentStatusHandlerProtocol(Protocol):
    async def handle(
        self, *, actor: User, lineage_id: UUID
    ) -> "ExamWorkspaceEnrichmentStatusResponse": ...
