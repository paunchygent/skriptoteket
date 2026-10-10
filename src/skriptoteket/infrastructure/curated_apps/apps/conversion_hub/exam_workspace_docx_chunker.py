"""Segment DOCX body text without interpreting exam content."""

import io
import zipfile

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph

# lxml is an external dependency without installed type stubs.
from lxml.etree import XMLSyntaxError  # type: ignore[import-untyped]

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.errors import DomainError, ErrorCode


def _table_text(table: Table) -> str:
    rows: list[str] = []
    has_text = False
    for row in table.rows:
        cells: list[str] = []
        # Physical cells keep merged-cell text from being repeated for each grid slot.
        for element in row._tr.tc_lst:
            cell = _Cell(element, table)
            cells.append(
                "\n".join(
                    block.text if isinstance(block, Paragraph) else _table_text(block)
                    for block in cell.iter_inner_content()
                )
            )
            has_text = has_text or bool(cells[-1].strip())
        rows.append(" | ".join(cells))
    return "\n".join(rows) if has_text else ""


class PythonDocxExamChunker:
    """Keep body order, source whitespace and stable body-child anchors."""

    def chunk(self, *, content: bytes) -> tuple[DocxChunk, ...]:
        chunks: list[DocxChunk] = []
        try:
            document = Document(io.BytesIO(content))
            for ordinal, element in enumerate(document.element.body, start=1):
                if isinstance(element, CT_P):
                    paragraph = Paragraph(element, document)
                    text = paragraph.text
                    style_name = paragraph.style.name if paragraph.style is not None else ""
                    kind = "heading" if style_name.startswith(("Heading", "Title")) else "paragraph"
                elif isinstance(element, CT_Tbl):
                    table = Table(element, document)
                    text = _table_text(table)
                    kind = "table"
                else:
                    continue
                if text.strip():
                    chunks.append(DocxChunk(anchor=f"body:{ordinal:04d}", kind=kind, text=text))
        except (
            PackageNotFoundError,
            zipfile.BadZipFile,
            XMLSyntaxError,
            KeyError,
            ValueError,
            OSError,
            AttributeError,
        ) as error:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Filen kunde inte läsas som ett Word-dokument (.docx).",
            ) from error

        if not chunks:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Word-dokumentet saknar läsbart innehåll.",
            )
        return tuple(chunks)
