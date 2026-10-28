"""Read a PDF exam with a text layer as the Word import's source (ST-SKRIPT-39-10 P5).

A teacher's exam saved as PDF from Word or Google Docs carries its words as positioned
characters. The PDF is read locally with pdfplumber into the chunk sequence the Word
chunker produces (paragraphs, headings, tables, pictures), so the existing Word
conversion path, its AI grouping, labeling, conversion and review, runs on it unchanged;
reading the PDF adds no AI call. Placed pictures and drawn figures are cut out of the
rendered page as pictures at their place in the reading order (TASK-SKRIPT-39-10-02).

Every page is judged by its text layer before it is laid out (ST-SKRIPT-39-10 P2, P7): a
page whose glyphs are mostly unmapped is skipped and named by its page number, a
picture-only page keeps its place, and a PDF with no readable text imports nothing and
stops with a message telling the teacher how to save the exam again.

Relationships:
    - ``PdfPlumberExamChunker`` implements ``DocxExamChunkerProtocol`` and
      ``PdfPlumberLabelerMarkdown`` implements ``LabelerSourceProtocol``; both read the
      same blocks, so the labeler's chunks carry the chunker's anchors.
    - ``exam_workspace_import_source`` sends PDF bytes here and DOCX bytes to the Word
      chunker and labeler.
    - ``exam_workspace_pdf_readability`` judges every page's glyphs and
      ``exam_workspace_pdf_layout`` skips the unreadable pages, naming them by number.
    - ``exam_workspace_pdf_pictures`` renders the pages that hold pictures.
    - pdfplumber is imported on first use, so the Word path never loads it.
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from dataclasses import dataclass, replace

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
    ChunkedSource,
    DocxExamChunkerProtocol,
    LabelerSource,
    LabelerSourceProtocol,
)

NO_READABLE_TEXT = (
    "Det gick inte att läsa in texten i PDF-filen. Spara provet som Word-fil eller som PDF "
    "från originaldokumentet och importera den nya filen."
)


def skipped_pages_note(pages: Sequence[int]) -> str:
    """One note naming the pages the reader skipped, in the copy the teacher sees.

    ``pages`` holds the 1-based pages whose text layer was unreadable, in page order; the
    note names each one by number and gives no ranges.
    """
    numbered = [str(page) for page in pages]
    if len(numbered) == 1:
        return f"Sida {numbered[0]} importerades inte eftersom texten inte gick att läsa in."
    return (
        f"Sidorna {', '.join(numbered[:-1])} och {numbered[-1]} importerades inte "
        "eftersom texten inte gick att läsa in."
    )


@dataclass(frozen=True)
class PdfRead:
    """One PDF's blocks in reading order and the 1-based pages the reader skipped."""

    blocks: tuple[PdfBlock, ...]
    skipped_pages: tuple[int, ...]


def read_pdf(content: bytes) -> PdfRead:
    """One text PDF read as blocks, naming the pages whose text layer is unreadable.

    Raises the Word chunker's two validation errors in PDF wording: a file that cannot be
    read as a PDF, and a PDF with no readable text. Pictures alone are no readable
    content: a PDF with no text stops even when it holds pictures, as does a PDF whose
    every page is unreadable, and that one stops before any page renders.
    """
    import pdfplumber
    from pdfminer.pdfparser import PDFSyntaxError
    from pdfminer.psexceptions import PSException
    from pdfplumber.utils.exceptions import PdfminerException
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pypdf_pages = list(PdfReader(io.BytesIO(content)).pages)
            pages = read_pages(pdf.pages, pypdf_pages)
    except (
        PdfminerException,
        PdfReadError,
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
    if len(pages.skipped_pages) == len(pypdf_pages):
        raise DomainError(code=ErrorCode.VALIDATION_ERROR, message=NO_READABLE_TEXT)
    blocks = pdf_blocks(with_pictures(content, pages.items))
    if not any(block.chunk.text.strip() for block in blocks):
        raise DomainError(code=ErrorCode.VALIDATION_ERROR, message=NO_READABLE_TEXT)
    return PdfRead(blocks=blocks, skipped_pages=pages.skipped_pages)


class PdfPlumberExamChunker(DocxExamChunkerProtocol):
    """Segment a text PDF into the Word import's chunks without interpreting exam items."""

    def chunk(self, *, content: bytes) -> ChunkedSource:
        read = read_pdf(content)
        notes = (skipped_pages_note(read.skipped_pages),) if read.skipped_pages else ()
        return ChunkedSource(chunks=tuple(block.chunk for block in read.blocks), notes=notes)


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
        for block in read_pdf(content).blocks:
            chunk = block.chunk
            chunks.append(replace(chunk, marked_text=block.markdown))
            for image in chunk.images:
                images[chunk.anchor] = image.payload
            for missing in chunk.missing_images:
                unavailable[chunk.anchor] = missing.reference
        return LabelerSource(chunks=tuple(chunks), images=images, unavailable=unavailable)
