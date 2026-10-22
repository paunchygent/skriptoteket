"""A Word exam with a picture and drawn figures, saved as PDF by Word, keeps them in place.

``metodprov_med_bilder.docx`` is ``metodprov_vetenskaplig_metod_med_facit.docx`` with a
picture (a chart PNG) in question 7 and two figures drawn with Word shapes and text-box
labels in questions 5 and 6, made in Microsoft Word on macOS, and ``.pdf`` is Word's own
export of it (real producer output). The Word import gives the drawn figures as drawing
chunks without a picture, since Word shapes carry none; the PDF import cuts each of them
out as a picture at the same place, so it holds every picture the Word import holds and
more.
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

import pytest
from PIL import Image

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_chunker import (  # noqa: E501
    PdfPlumberExamChunker,
)

_FIXTURES = Path("tests/fixtures/exam_conversion/pdf_corpus")
_DOCX = _FIXTURES / "metodprov_med_bilder.docx"
_PDF = _FIXTURES / "metodprov_med_bilder.pdf"
# Text in the drawn figures' text boxes: drawn, not typed, in both imports.
_FIGURE_LABELS = (
    "Svenska gymnasieelever (populationen)",
    "Elever på ett program",
    "Alla elever på skolan",
    "Elever som är i biblioteket",
    "Svarar på frågan",
)
_WHITE = 200


def _chunks() -> tuple[tuple[DocxChunk, ...], tuple[DocxChunk, ...]]:
    return (
        PythonDocxExamChunker().chunk(content=_DOCX.read_bytes()),
        PdfPlumberExamChunker().chunk(content=_PDF.read_bytes()),
    )


def _words(text: str) -> str:
    """The text's words; a PDF keeps no non-breaking space, so a line Word kept together
    may read as a line break."""
    return " ".join(text.replace("\xa0", " ").split())


def _places(chunks: tuple[DocxChunk, ...]) -> list[tuple[str, str]]:
    """Each drawing's place: the text right before it and right after it."""
    return [
        (_words(chunks[index - 1].text), _words(chunks[index + 1].text))
        for index, chunk in enumerate(chunks)
        if chunk.kind == "drawing"
    ]


@pytest.mark.parametrize("path", [_DOCX, _PDF], ids=["docx", "pdf"])
def test_fixtures_are_the_recorded_word_files(path: Path) -> None:
    recorded = Path(f"{path}.sha256").read_text(encoding="utf-8").split()[0]

    assert hashlib.sha256(path.read_bytes()).hexdigest() == recorded


def test_every_word_picture_and_figure_is_a_pdf_picture_in_the_same_place() -> None:
    docx, pdf = _chunks()

    assert _places(pdf) == _places(docx)
    assert len(_places(pdf)) == 3
    assert [len(chunk.images) for chunk in docx if chunk.kind == "drawing"] == [0, 0, 1]
    assert [len(chunk.images) for chunk in pdf if chunk.kind == "drawing"] == [1, 1, 1]
    assert [chunk.anchor for chunk in pdf] == [chunk.anchor for chunk in docx]


def test_the_placed_picture_keeps_its_shape() -> None:
    docx, pdf = _chunks()
    (word,) = [image for chunk in docx for image in chunk.images]
    pdf_drawings = [chunk for chunk in pdf if chunk.kind == "drawing"]
    cut = pdf_drawings[-1].images[0]

    assert word.width is not None and word.height is not None
    assert cut.width is not None and cut.height is not None
    assert abs(cut.width / cut.height - word.width / word.height) < 0.03


def test_text_is_the_word_text_and_figure_labels_are_not_read_as_text() -> None:
    docx, pdf = _chunks()

    assert [_words(chunk.text) for chunk in pdf] == [_words(chunk.text) for chunk in docx]
    for label in _FIGURE_LABELS:
        assert not any(label in _words(chunk.text) for chunk in pdf), label


def test_each_drawn_figure_is_cut_with_a_white_margin_on_every_side() -> None:
    _, pdf = _chunks()
    figures = [chunk.images[0] for chunk in pdf if chunk.kind == "drawing"][:2]

    for figure in figures:
        image = Image.open(io.BytesIO(figure.payload)).convert("L")
        ink = image.point(lambda value: 255 if value < _WHITE else 0).getbbox()
        assert ink is not None
        left, top, right, bottom = ink
        assert min(left, top, image.width - right, image.height - bottom) >= 4
