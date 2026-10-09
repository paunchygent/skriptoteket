"""Protocol seams for the native exam workspace (ST-SKRIPT-39-04)."""

from typing import Protocol
from uuid import UUID

from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_extraction import (
    DocxExtractionResult,
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
