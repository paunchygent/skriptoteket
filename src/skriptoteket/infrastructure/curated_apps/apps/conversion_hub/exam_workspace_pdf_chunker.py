"""Read a PDF exam with a text layer as the Word import's source (ST-SKRIPT-39-10 P5).

A teacher's exam saved as PDF from Word or Google Docs carries its words as positioned
characters. The PDF is read locally with pdfplumber into the chunk sequence the Word
chunker produces (paragraphs, headings, tables, pictures), so the existing Word
conversion path, its AI grouping, labeling, conversion and review, runs on it unchanged;
reading the PDF adds no AI call. Placed pictures and drawn figures are cut out of the
rendered page as pictures at their place in the reading order (TASK-SKRIPT-39-10-02).

Relationships:
    - ``PdfPlumberExamChunker`` implements ``DocxExamChunkerProtocol`` and
      ``PdfPlumberLabelerMarkdown`` implements ``LabelerSourceProtocol``; both read the
      same blocks, so the labeler's chunks carry the chunker's anchors.
    - ``exam_workspace_import_source`` sends PDF bytes here and DOCX bytes to the Word
      chunker and labeler.
    - ``exam_workspace_pdf_pictures`` renders the pages that hold pictures.
    - pdfplumber is imported on first use, so the Word path never loads it.
"""

from __future__ import annotations

import io
from dataclasses import replace

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_blocks import (  # noqa: E501
    PdfBlock,
    pdf_blocks,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_layout import (  # noqa: E501
    read_pages,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_pictures import (  # noqa: E501
    with_pictures,
)
from skriptoteket.protocols.exam_workspace import (
    DocxExamChunkerProtocol,
    LabelerSource,
    LabelerSourceProtocol,
)


def read_pdf_blocks(content: bytes) -> tuple[PdfBlock, ...]:
    """Every block of one text PDF in reading order, anchored like the Word chunker.

    Raises the Word chunker's two validation errors in PDF wording: a file that cannot be
    read as a PDF, and a PDF with no text. Pictures alone are no readable content: a PDF
    without text is the no-text case even when it holds pictures.
    """
    import pdfplumber
    from pdfminer.pdfparser import PDFSyntaxError
    from pdfminer.psexceptions import PSException
    from pdfplumber.utils.exceptions import PdfminerException

    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            items = read_pages(pdf.pages)
    except (
        PdfminerException,
        PDFSyntaxError,
        PSException,
        ValueError,
        KeyError,
        TypeError,
    ) as error:
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Filen kunde inte läsas som en PDF-fil (.pdf).",
        ) from error
    blocks = pdf_blocks(with_pictures(content, items))
    if not any(block.chunk.text.strip() for block in blocks):
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="PDF-filen saknar läsbart innehåll.",
        )
    return blocks


class PdfPlumberExamChunker(DocxExamChunkerProtocol):
    """Segment a text PDF into the Word import's chunks without interpreting exam items."""

    def chunk(self, *, content: bytes) -> tuple[DocxChunk, ...]:
        return tuple(block.chunk for block in read_pdf_blocks(content))


class PdfPlumberLabelerMarkdown(LabelerSourceProtocol):
    """The labeler's faithful source of a text PDF (D14): every block as markdown.

    A text block is text the reader rebuilt, so markdown carries it. A picture block has
    no markdown and its cut picture as its image, as the Word labeler images a drawn
    block; a picture that could not be cut is unavailable under its name.
    """

    def source(self, *, content: bytes) -> LabelerSource:
        chunks: list[DocxChunk] = []
        images: dict[str, bytes] = {}
        unavailable: dict[str, str] = {}
        for block in read_pdf_blocks(content):
            chunk = block.chunk
            chunks.append(replace(chunk, marked_text=block.markdown))
            for image in chunk.images:
                images[chunk.anchor] = image.payload
            for missing in chunk.missing_images:
                unavailable[chunk.anchor] = missing.reference
        return LabelerSource(chunks=tuple(chunks), images=images, unavailable=unavailable)
