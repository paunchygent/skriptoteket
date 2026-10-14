"""Protocol seams for the native exam workspace (ST-SKRIPT-39-04)."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol
from uuid import UUID

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceAnswerKeySuggestionsResponse,
    ExamWorkspaceConversionStatus,
    ExamWorkspaceDocumentListResponse,
    ExamWorkspaceDocumentResponse,
    ExamWorkspaceExportFile,
    ExamWorkspaceExportTarget,
    ExamWorkspaceItemRetryResponse,
    RequestExamWorkspaceAnswerKeySuggestionsRequest,
    RetryExamWorkspaceItemRequest,
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


class DocxExamChunkerProtocol(Protocol):
    """Segment ordered source text without interpreting exam items."""

    def chunk(self, *, content: bytes) -> tuple[DocxChunk, ...]: ...


@dataclass(frozen=True)
class LabelerSource:
    """The labeler's faithful source of one DOCX (D14), block by block in source order.

    Each chunk carries its block's markdown. A block markdown cannot carry has empty
    markdown and either a PNG of that block in ``images`` or, when no faithful image could
    be made, the reason in ``unavailable``; both are keyed by chunk anchor.
    """

    chunks: tuple[DocxChunk, ...]
    images: Mapping[str, bytes]
    unavailable: Mapping[str, str]


class LabelerSourceProtocol(Protocol):
    """Project a DOCX into the labeler's faithful source."""

    def source(self, *, content: bytes) -> LabelerSource: ...


class ExamWorkspaceContainerCodecProtocol(Protocol):
    """Fail-closed (de)serialization of versioned exam workspace containers."""

    def build(self, *, content: ExamWorkspaceContainerContent) -> bytes: ...

    def parse(self, *, content: bytes) -> ExamWorkspaceContainerContent: ...


@dataclass(frozen=True)
class ExamWorkspaceAssetContent:
    """One picture payload with the media type its document asset declares."""

    content: bytes
    media_type: str


class GetExamWorkspaceAssetHandlerProtocol(Protocol):
    """Read one declared picture payload of the actor-owned head revision."""

    async def handle(
        self, *, actor: User, lineage_id: UUID, asset_id: str
    ) -> ExamWorkspaceAssetContent: ...


class ExamWorkspaceDocxWriterProtocol(Protocol):
    """Minimal validated DOCX writer for native exam documents (D3)."""

    def build_docx_bytes(
        self,
        document: "NativeExamDocument",
        *,
        assets_by_id: Mapping[str, bytes] = MappingProxyType({}),
    ) -> bytes: ...

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


class RequestExamWorkspaceAnswerKeySuggestionsHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        request: RequestExamWorkspaceAnswerKeySuggestionsRequest,
    ) -> ExamWorkspaceAnswerKeySuggestionsResponse: ...


class GetExamWorkspaceAnswerKeySuggestionsStatusHandlerProtocol(Protocol):
    async def handle(
        self, *, actor: User, lineage_id: UUID, job_id: UUID
    ) -> ExamWorkspaceAnswerKeySuggestionsResponse: ...


class FindExamWorkspaceAnswerKeySuggestionsHandlerProtocol(Protocol):
    async def handle(
        self, *, actor: User, lineage_id: UUID, document_revision: int
    ) -> ExamWorkspaceAnswerKeySuggestionsResponse | None: ...


class RetryExamWorkspaceItemHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        request: RetryExamWorkspaceItemRequest,
    ) -> ExamWorkspaceItemRetryResponse: ...
