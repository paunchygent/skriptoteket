"""Protocol seams for the native exam workspace (ST-SKRIPT-39-04)."""

from typing import Protocol
from uuid import UUID

from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_extraction import (
    DocxExtractionResult,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)


class DocxExamExtractorProtocol(Protocol):
    """Deterministic DOCX-to-native-exam extraction behind infrastructure."""

    def extract(
        self, *, document_id: UUID, filename: str, content: bytes
    ) -> DocxExtractionResult: ...


class ExamWorkspaceContainerCodecProtocol(Protocol):
    """Fail-closed (de)serialization of versioned exam workspace containers."""

    def build(self, *, content: ExamWorkspaceContainerContent) -> bytes: ...

    def parse(self, *, content: bytes) -> ExamWorkspaceContainerContent: ...


class ExamWorkspaceDocxWriterProtocol(Protocol):
    """Minimal validated DOCX writer for native exam documents (D3)."""

    def build_docx_bytes(self, document: "NativeExamDocument") -> bytes: ...

    def validate_docx_bytes(self, content: bytes, *, expected_item_count: int) -> None: ...
