"""A Word corpus exam saved as PDF from Microsoft Word reads as the Word file's chunks.

The fixture is ``bf26_english_1_unit_test_kap_1_2_med_facit.docx`` exported to PDF by
Word on macOS (real producer output). Two differences are the PDF's, not the reader's: a
PDF keeps no non-breaking spaces, and a blank soft-broken line (Shift+Enter twice) prints
like a paragraph break, so that Word paragraph reads as two chunks.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_chunker import (  # noqa: E501
    PdfPlumberExamChunker,
)

_NAME = "bf26_english_1_unit_test_kap_1_2_med_facit"
_DOCX = Path(f"tests/fixtures/exam_conversion/docx_corpus/{_NAME}.docx")
_PDF = Path(f"tests/fixtures/exam_conversion/pdf_corpus/{_NAME}.pdf")
_ITALIC = re.compile(r"<i>(.*?)</i>", re.DOTALL)
_BLANK_SOFT_BREAK = "\n\n"


def _plain(text: str) -> str:
    return text.replace("\xa0", " ")


def _chunks() -> tuple[tuple[DocxChunk, ...], tuple[DocxChunk, ...]]:
    return (
        PythonDocxExamChunker().chunk(content=_DOCX.read_bytes()),
        PdfPlumberExamChunker().chunk(content=_PDF.read_bytes()),
    )


def test_fixture_is_the_recorded_word_export() -> None:
    recorded = Path(f"{_PDF}.sha256").read_text(encoding="utf-8").split()[0]

    assert hashlib.sha256(_PDF.read_bytes()).hexdigest() == recorded


def test_every_word_paragraph_is_one_pdf_chunk_or_two_at_a_blank_soft_break() -> None:
    docx, pdf = _chunks()

    position, splits = 0, 0
    for chunk in docx:
        text = _plain(chunk.text)
        if _plain(pdf[position].text) == text:
            position += 1
            continue
        assert _BLANK_SOFT_BREAK in text, chunk.anchor
        joined = f"{_plain(pdf[position].text)}{_BLANK_SOFT_BREAK}{_plain(pdf[position + 1].text)}"
        assert joined == text, chunk.anchor
        position += 2
        splits += 1

    assert position == len(pdf)
    assert splits == 6
    assert [chunk.anchor for chunk in pdf] == [f"body:{n:04d}" for n in range(1, len(pdf) + 1)]


def test_tables_headings_and_italic_facit_match_the_word_file() -> None:
    docx, pdf = _chunks()

    def tables(chunks: tuple[DocxChunk, ...]) -> list[str]:
        return [_plain(chunk.text) for chunk in chunks if chunk.kind == "table"]

    def headings(chunks: tuple[DocxChunk, ...]) -> list[tuple[str, int | None]]:
        return [
            (_plain(chunk.text), chunk.paragraphs[0].heading_level)
            for chunk in chunks
            if chunk.kind == "heading"
        ]

    def italic(chunks: tuple[DocxChunk, ...]) -> list[str]:
        return [_plain(span) for chunk in chunks for span in _ITALIC.findall(chunk.marked_text)]

    assert tables(pdf) == tables(docx)
    assert len(tables(pdf)) > 0
    assert headings(pdf) == headings(docx)
    assert len(headings(pdf)) > 0
    assert italic(pdf) == italic(docx)
    assert len(italic(pdf)) > 0
