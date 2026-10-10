"""Protocol seams for the native exam workspace (ST-SKRIPT-39-04)."""

from typing import Protocol

from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
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
