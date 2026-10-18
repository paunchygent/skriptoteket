"""Protocol seams for the native exam workspace (ST-SKRIPT-39-04)."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol
from uuid import UUID

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamCourseCatalogResponse,
    ExamWorkspaceAnswerKeySuggestionsResponse,
    ExamWorkspaceConversionStatus,
    ExamWorkspaceDocumentListResponse,
    ExamWorkspaceDocumentResponse,
    ExamWorkspaceExportChecklistResponse,
    ExamWorkspaceExportFile,
    ExamWorkspaceExportTarget,
    ExamWorkspaceItemRetryResponse,
    RequestExamWorkspaceAnswerKeySuggestionsRequest,
    RetryExamWorkspaceItemRequest,
    SaveExamWorkspaceDocumentRequest,
)
from skriptoteket.application.curated_apps.exam_workspace_history import (
    ExamWorkspaceHistoryDocumentResponse,
    ExamWorkspaceHistoryResponse,
    SaveAsExamWorkspaceDocumentRequest,
)
from skriptoteket.application.curated_apps.exam_workspace_misspellings import (
    ExamWorkspaceMisspellingsRequest,
    ExamWorkspaceMisspellingsResponse,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_import_contracts import (
    ExamNetQtiPackageSource,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault import VaultFile


class GenerateExamWorkspaceMisspellingsHandlerProtocol(Protocol):
    def handle(
        self, *, request: ExamWorkspaceMisspellingsRequest
    ) -> ExamWorkspaceMisspellingsResponse: ...


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
        self, *, actor: User, filename: str, content: bytes, course_key: str | None
    ) -> ExamWorkspaceConversionStatus: ...


class ImportExamWorkspaceDigiExamDocumentHandlerProtocol(Protocol):
    async def handle(
        self, *, actor: User, filename: str, content: bytes, course_key: str | None
    ) -> ExamWorkspaceConversionStatus: ...


class GetExamCourseCatalogHandlerProtocol(Protocol):
    async def handle(self, *, actor: User) -> ExamCourseCatalogResponse: ...


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

    async def history(self, *, actor: User, lineage_id: UUID) -> ExamWorkspaceHistoryResponse: ...

    async def history_step(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        step_id: UUID,
    ) -> ExamWorkspaceHistoryDocumentResponse: ...

    async def save_as(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        request: SaveAsExamWorkspaceDocumentRequest,
    ) -> ExamWorkspaceDocumentResponse: ...


class ExportExamWorkspaceDocumentHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        target: ExamWorkspaceExportTarget,
        expected_revision: int,
    ) -> ExamWorkspaceExportFile: ...

    async def save(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        target: ExamWorkspaceExportTarget,
        expected_revision: int,
    ) -> VaultFile: ...

    async def checklist(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        expected_revision: int,
    ) -> ExamWorkspaceExportChecklistResponse: ...


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


class ExamNetQtiPackageReaderProtocol(Protocol):
    """Open an uploaded QTI 3.0 package; refuse unsafe or malformed archives in Swedish."""

    def read(self, *, content: bytes) -> ExamNetQtiPackageSource: ...
