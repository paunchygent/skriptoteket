"""Send a Word-lane import's bytes to the reader of their file format (ST-SKRIPT-39-10 P5).

The Word import lane converts Word files (.docx) and text PDFs (.pdf) through one path,
and the job keeps only the uploaded bytes; ``is_pdf`` tells the format from them. Each
reader returns the same chunk shapes, so nothing after this seam knows which format the
teacher uploaded.

Relationships:
    - Bound in ``di.exam_workspace`` (the job's chunker) and ``di.docx_conversion`` (the
      pipeline's labeler source).
    - ``ImportExamWorkspaceDocumentHandler`` admits a ``.pdf`` only when ``is_pdf`` holds.
"""

from __future__ import annotations

from skriptoteket.domain.curated_apps.exam_workspace.import_file_format import is_pdf
from skriptoteket.protocols.exam_workspace import (
    ChunkedSource,
    DocxExamChunkerProtocol,
    LabelerSource,
    LabelerSourceProtocol,
)


class ImportSourceChunker(DocxExamChunkerProtocol):
    """Chunk Word or PDF bytes with the chunker of their format."""

    def __init__(self, *, docx: DocxExamChunkerProtocol, pdf: DocxExamChunkerProtocol) -> None:
        self._docx = docx
        self._pdf = pdf

    def chunk(self, *, content: bytes) -> ChunkedSource:
        reader = self._pdf if is_pdf(content) else self._docx
        return reader.chunk(content=content)


class ImportLabelerSource(LabelerSourceProtocol):
    """Project Word or PDF bytes into the labeler's source with the projector of their format."""

    def __init__(self, *, docx: LabelerSourceProtocol, pdf: LabelerSourceProtocol) -> None:
        self._docx = docx
        self._pdf = pdf

    def source(self, *, content: bytes) -> LabelerSource:
        reader = self._pdf if is_pdf(content) else self._docx
        return reader.source(content=content)
