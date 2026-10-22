"""Source-preservation proof for the DOCX chunking adapter."""

import io
import zipfile
from dataclasses import replace
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


def _text_projection(chunks: tuple[DocxChunk, ...]) -> tuple[DocxChunk, ...]:
    """The chunks as the text projection: text, marked text and pictures, no formatting."""
    return tuple(replace(chunk, runs=(), paragraphs=()) for chunk in chunks)


def test_quiz_preserves_all_paragraphs_and_soft_break_options() -> None:
    content = _QUIZ.read_bytes()
    chunks = PythonDocxExamChunker().chunk(content=content)

    assert len(chunks) == 109
    assert tuple(chunk.text for chunk in chunks) == tuple(
        paragraph.text for paragraph in Document(io.BytesIO(content)).paragraphs
    )
    assert (chunks[4].anchor, chunks[4].kind, chunks[4].text, chunks[4].marked_text) == (
        "body:0007",
        "paragraph",
        "A. deep\nB. strange\nC. dignified\nD. thrifty",
        "A. deep\nB. strange\nC. dignified\nD. thrifty",
    )
    assert chunks[5].text == "Correct answer: A. deep"
    assert chunks[5].marked_text == "Correct answer: <i>A. deep</i>"
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

    first = PythonDocxExamChunker().chunk(content=content)

    assert _text_projection(first) == (
        DocxChunk("body:0001", "heading", "  A heading  ", "  A heading  "),
        DocxChunk("body:0003", "paragraph", "  First\nsecond\tline  ", "  First\nsecond\tline  "),
        DocxChunk(
            "body:0004",
            "table",
            "  Cell\nsoft break  \nAnother paragraph | Right\nBottom | ",
            "  Cell\nsoft break  \nAnother paragraph | Right\nBottom | ",
        ),
        DocxChunk("body:0005", "paragraph", "After the table", "After the table"),
        DocxChunk("body:0006", "table", "Second table", "Second table"),
    )
    assert PythonDocxExamChunker().chunk(content=content) == first


def test_merged_and_nested_cells_preserve_text_once_in_order() -> None:
    document = Document()
    table = document.add_table(rows=1, cols=2)
    cell = table.cell(0, 0).merge(table.cell(0, 1))
    cell.text = "Before"
    nested = cell.add_table(rows=1, cols=1)
    nested.cell(0, 0).text = "Nested\nlines"
    cell.paragraphs[-1].text = "After"

    assert _text_projection(PythonDocxExamChunker().chunk(content=_bytes(document))) == (
        DocxChunk(
            "body:0001", "table", "Before\nNested\nlines\nAfter", "Before\nNested\nlines\nAfter"
        ),
    )


def test_course_exam_marks_teacher_italics_only_in_model_text() -> None:
    content = _QUIZ.with_name("svenska_2_kursavslutande_prov_med_facit.docx").read_bytes()
    chunks = {chunk.anchor: chunk for chunk in PythonDocxExamChunker().chunk(content=content)}

    assert chunks["body:0086"].text == (
        "a) De väntar inte. är en huvudsats\n"
        "b) I bisatsen att de inte väntar står satsadverbialet före det finita verbet."
    )
    assert chunks["body:0086"].marked_text == (
        "a) <i>De väntar inte.</i> är en <i>huvudsats</i>\n"
        "b) I bisatsen <i>att de inte väntar</i> står satsadverbialet <i>före</i> "
        "det finita verbet."
    )
    assert chunks["body:0063"].marked_text.startswith(
        "a) I ordet lekfullheten är <i>lek</i> <i>R</i>"
    )


def test_italic_runs_in_paragraphs_and_tables_are_marked() -> None:
    document = Document()
    paragraph = document.add_paragraph("Svar: ")
    paragraph.add_run("två ").italic = True
    paragraph.add_run("ord").italic = True
    paragraph.add_run(" slut")
    cell = document.add_table(rows=1, cols=1).cell(0, 0)
    cell.paragraphs[0].add_run("Cell ")
    cell.paragraphs[0].add_run("svar").italic = True

    chunks = PythonDocxExamChunker().chunk(content=_bytes(document))

    assert [(c.text, c.marked_text) for c in chunks] == [
        ("Svar: två ord slut", "Svar: <i>två ord</i> slut"),
        ("Cell svar", "Cell <i>svar</i>"),
    ]


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
