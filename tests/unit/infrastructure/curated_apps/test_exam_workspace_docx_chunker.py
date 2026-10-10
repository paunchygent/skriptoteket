"""Source-preservation proof for the DOCX chunking adapter."""

import io
import zipfile
from pathlib import Path

import pytest
from docx import Document
from docx.document import Document as DocxDocument

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)

_QUIZ = Path(
    "tests/fixtures/exam_conversion/docx_corpus/chapter_4_poetry_and_lyrics_quiz_med_facit.docx"
)


def _bytes(document: DocxDocument) -> bytes:
    stream = io.BytesIO()
    document.save(stream)
    return stream.getvalue()


def test_quiz_preserves_all_paragraphs_and_soft_break_options() -> None:
    content = _QUIZ.read_bytes()
    chunks = PythonDocxExamChunker().chunk(content=content)

    assert len(chunks) == 109
    assert tuple(chunk.text for chunk in chunks) == tuple(
        paragraph.text for paragraph in Document(io.BytesIO(content)).paragraphs
    )
    assert chunks[4] == DocxChunk(
        anchor="body:0007",
        kind="paragraph",
        text="A. deep\nB. strange\nC. dignified\nD. thrifty",
    )
    assert chunks[5].text == "Correct answer: A. deep"
    assert chunks[-1].text == "Correct answer: alliteration"


def test_body_order_anchors_and_whitespace_survive_tables_and_empty_paragraphs() -> None:
    document = Document()
    document.add_heading("  A heading  ", level=2)
    document.add_paragraph("")
    document.add_paragraph("  First\nsecond\tline  ")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "  Cell\nsoft break  "
    table.cell(0, 0).add_paragraph("Another paragraph")
    table.cell(0, 1).text = "Right"
    table.cell(1, 0).text = "Bottom"
    document.add_paragraph("After the table")
    second_table = document.add_table(rows=1, cols=1)
    second_table.cell(0, 0).text = "Second table"
    content = _bytes(document)

    chunks = PythonDocxExamChunker().chunk(content=content)

    assert chunks == (
        DocxChunk("body:0001", "heading", "  A heading  "),
        DocxChunk("body:0003", "paragraph", "  First\nsecond\tline  "),
        DocxChunk(
            "body:0004", "table", "  Cell\nsoft break  \nAnother paragraph | Right\nBottom | "
        ),
        DocxChunk("body:0005", "paragraph", "After the table"),
        DocxChunk("body:0006", "table", "Second table"),
    )
    assert PythonDocxExamChunker().chunk(content=content) == chunks


def test_merged_and_nested_cells_preserve_text_once_in_order() -> None:
    document = Document()
    table = document.add_table(rows=1, cols=2)
    cell = table.cell(0, 0).merge(table.cell(0, 1))
    cell.text = "Before"
    nested = cell.add_table(rows=1, cols=1)
    nested.cell(0, 0).text = "Nested\nlines"
    cell.paragraphs[-1].text = "After"

    assert PythonDocxExamChunker().chunk(content=_bytes(document)) == (
        DocxChunk("body:0001", "table", "Before\nNested\nlines\nAfter"),
    )


@pytest.mark.parametrize("content", [b"", b"not a docx", b"PK\x03\x04truncated"])
def test_invalid_docx_reports_swedish_domain_error(content: bytes) -> None:
    with pytest.raises(DomainError) as exc_info:
        PythonDocxExamChunker().chunk(content=content)

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert exc_info.value.message == "Filen kunde inte läsas som ett Word-dokument (.docx)."


def test_malformed_document_xml_reports_domain_error() -> None:
    stream = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(_bytes(Document()))) as source:
        with zipfile.ZipFile(stream, "w") as target:
            for entry in source.infolist():
                target.writestr(
                    entry,
                    b"<broken" if entry.filename == "word/document.xml" else source.read(entry),
                )

    with pytest.raises(DomainError) as exc_info:
        PythonDocxExamChunker().chunk(content=stream.getvalue())

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "Word-dokument" in exc_info.value.message


@pytest.mark.parametrize("layout", ["empty", "whitespace", "table"])
def test_empty_docx_reports_swedish_domain_error(layout: str) -> None:
    document = Document()
    if layout == "whitespace":
        document.add_paragraph(" \t\n ")
    elif layout == "table":
        document.add_table(rows=2, cols=2)

    with pytest.raises(DomainError) as exc_info:
        PythonDocxExamChunker().chunk(content=_bytes(document))

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert exc_info.value.message == "Word-dokumentet saknar läsbart innehåll."
