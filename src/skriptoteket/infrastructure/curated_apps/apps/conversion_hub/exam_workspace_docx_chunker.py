"""Segment DOCX body blocks, text or drawn, without interpreting exam content."""

import io
import zipfile

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from docx.oxml.ns import qn
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.oxml.xmlchemy import BaseOxmlElement
from docx.table import Table, _Cell
from docx.text.hyperlink import Hyperlink
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.errors import DomainError, ErrorCode

# Drawn content: pictures, text boxes and embedded objects. Its words, if any, are not in
# the block's plain text, so a block holding only drawn content is still source.
DRAWN = tuple(qn(tag) for tag in ("w:drawing", "w:pict", "w:object", "w:txbxContent"))


def drawn(element: BaseOxmlElement) -> bool:
    return any(next(element.iter(tag), None) is not None for tag in DRAWN)


def _marked_paragraph(paragraph: Paragraph) -> str:
    """Paragraph text with each directly italic stretch wrapped in <i>...</i>.

    Teachers write inline facit in italics. Adjacent italic runs share one tag; edge
    whitespace stays outside it.
    """
    runs: list[Run] = []
    for content in paragraph.iter_inner_content():
        runs.extend(content.runs if isinstance(content, Hyperlink) else (content,))
    stretches: list[tuple[bool, str]] = []
    for run in runs:
        italic = bool(run.italic)
        if stretches and stretches[-1][0] == italic:
            stretches[-1] = (italic, stretches[-1][1] + run.text)
        else:
            stretches.append((italic, run.text))
    marked: list[str] = []
    for italic, text in stretches:
        core = text.strip()
        if italic and core:
            start = text.index(core)
            text = f"{text[:start]}<i>{core}</i>{text[start + len(core) :]}"
        marked.append(text)
    return "".join(marked)


def _table_text(table: Table, *, marked: bool) -> str:
    rows: list[str] = []
    has_text = False
    for row in table.rows:
        cells: list[str] = []
        # Physical cells keep merged-cell text from being repeated for each grid slot.
        for element in row._tr.tc_lst:
            cell = _Cell(element, table)
            cells.append(
                "\n".join(
                    (_marked_paragraph(block) if marked else block.text)
                    if isinstance(block, Paragraph)
                    else _table_text(block, marked=marked)
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
                    marked_text = _marked_paragraph(paragraph)
                    style_name = paragraph.style.name if paragraph.style is not None else ""
                    kind = "heading" if style_name.startswith(("Heading", "Title")) else "paragraph"
                    if not text.strip() and drawn(element):
                        kind = "drawing"
                elif isinstance(element, CT_Tbl):
                    table = Table(element, document)
                    text = _table_text(table, marked=False)
                    marked_text = _table_text(table, marked=True)
                    kind = "table"
                else:
                    continue
                if text.strip() or drawn(element):
                    chunks.append(
                        DocxChunk(
                            anchor=f"body:{ordinal:04d}",
                            kind=kind,
                            text=text,
                            marked_text=marked_text,
                        )
                    )
        except (
            PackageNotFoundError,
            zipfile.BadZipFile,
            SyntaxError,
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
