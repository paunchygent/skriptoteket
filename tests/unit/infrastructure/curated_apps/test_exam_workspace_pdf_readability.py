"""Unreadable PDF pages are skipped and named, and a PDF with no text stops (D1-D3)."""

from __future__ import annotations

import io
from pathlib import Path

import pdfplumber
import pytest

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_chunker import (  # noqa: E501
    NO_READABLE_TEXT,
    PdfPlumberExamChunker,
    read_pdf,
    skipped_pages_note,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_items import (  # noqa: E501
    PdfWord,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_readability import (  # noqa: E501
    page_readable,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_pdf_picture_test_support import (
    PICTURE_SIZE,
    picture_tag,
    solid_png,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_pdf_test_support import (
    garbled,
    merged,
    pdf_bytes,
    picture_only_pdf,
)

_CORPUS = Path("tests/fixtures/exam_conversion/pdf_corpus")
# Two paragraphs on separate pages; an empty paragraph is a page with no glyph at all.
_FIRST = "<p>1. Vad heter huvudpersonen?</p>"
_THIRD = "<p>3. Vilken färg har båten?</p>"
_BREAK = '<p style="page-break-before: always">{body}</p>'
# A printed footer naming its page, as WeasyPrint typesets a page-number field.
_FOOTER = '<p style="position: fixed; bottom: 0; font-size: 8pt">Sida {page} av 3</p>'


def _page(*texts: str) -> tuple[PdfWord, ...]:
    """Words as the page reader gives them, one per argument, without page geometry."""
    return tuple(
        PdfWord(
            text=text,
            x0=0.0,
            x1=1.0,
            top=0.0,
            bottom=1.0,
            size=11.0,
            bold=False,
            italic=False,
        )
        for text in texts
    )


def _texts(content: bytes) -> list[str]:
    return [block.chunk.text for block in read_pdf(content).blocks]


@pytest.mark.parametrize(
    ("words", "readable"),
    [
        (_page("Fråga 1.", "Vad", "heter", "huvudpersonen?"), True),
        (_page("(cid:20)(cid:17)(cid:3)(cid:21)"), False),
        (_page("(cid:20)" * 6, "abcd"), False),
        (_page("(cid:20)" * 4, "abcdef"), True),
        (_page("\ufffd" * 5), False),
        (_page("\ue000\ue001", "\U000f0000"), False),
        (_page(), False),
    ],
    ids=[
        "swedish",
        "all-cid",
        "60-percent-cid",
        "40-percent-cid",
        "replacement",
        "private-use",
        "no-words",
    ],
)
def test_page_readable_counts_mapped_and_unmapped_glyphs(
    words: tuple[PdfWord, ...], readable: bool
) -> None:
    assert page_readable(words) is readable


@pytest.mark.parametrize(
    "content",
    [
        pdf_bytes("<p></p>"),
        picture_only_pdf(),
        garbled(pdf_bytes(_FIRST + _BREAK.format(body=_THIRD))),
    ],
    ids=["no-text", "pictures-only", "garbled-on-every-page"],
)
def test_a_pdf_without_readable_text_stops_with_the_new_message(content: bytes) -> None:
    with pytest.raises(DomainError) as read:
        read_pdf(content)
    with pytest.raises(DomainError) as chunked:
        PdfPlumberExamChunker().chunk(content=content).chunks

    assert read.value.code is ErrorCode.VALIDATION_ERROR
    assert read.value.message == NO_READABLE_TEXT
    assert chunked.value.code is ErrorCode.VALIDATION_ERROR
    assert chunked.value.message == NO_READABLE_TEXT


def test_a_pdf_that_stops_cuts_no_picture(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_: object, **__: object) -> None:
        raise AssertionError("a PDF that stops cuts no picture")

    monkeypatch.setattr(
        "skriptoteket.infrastructure.curated_apps.apps.conversion_hub."
        "exam_workspace_pdf_chunker.with_pictures",
        forbidden,
    )
    content = garbled(
        pdf_bytes(
            _FIRST + f"<p>{picture_tag(solid_png(*PICTURE_SIZE), 'width:120pt;height:80pt')}</p>"
        )
    )

    with pytest.raises(DomainError) as raised:
        read_pdf(content)

    assert raised.value.message == NO_READABLE_TEXT


def test_the_picture_only_fixture_holds_an_image_and_no_words() -> None:
    with pdfplumber.open(io.BytesIO(picture_only_pdf())) as pdf:
        (page,) = pdf.pages

        assert page.images
        assert page.dedupe_chars().extract_words() == []


def test_a_textless_page_between_text_pages_is_skipped_and_named() -> None:
    content = merged(pdf_bytes(_FIRST), pdf_bytes("<p></p>"), pdf_bytes(_THIRD))

    read = read_pdf(content)

    assert read.skipped_pages == (2,)
    assert [block.chunk.text for block in read.blocks] == [
        "1. Vad heter huvudpersonen?",
        "3. Vilken färg har båten?",
    ]


def test_a_page_number_after_a_skipped_page_is_dropped_by_its_real_page() -> None:
    content = merged(
        pdf_bytes(_FIRST + _FOOTER.format(page=1)),
        pdf_bytes("<p></p>"),
        pdf_bytes(_THIRD + _FOOTER.format(page=3)),
    )

    read = read_pdf(content)

    assert read.skipped_pages == (2,)
    texts = _texts(content)
    assert not any("Sida 1 av 3" in text or "Sida 3 av 3" in text for text in texts)
    assert texts == ["1. Vad heter huvudpersonen?", "3. Vilken färg har båten?"]


def test_a_garbled_page_between_text_pages_is_skipped_and_carries_no_glyphs() -> None:
    content = merged(pdf_bytes(_FIRST), garbled(pdf_bytes(_FIRST)), pdf_bytes(_FIRST))

    read = read_pdf(content)

    assert read.skipped_pages == (2,)
    assert _texts(content) == [
        "1. Vad heter huvudpersonen?",
        "1. Vad heter huvudpersonen?",
    ]
    assert not any("(cid:" in block.chunk.text for block in read.blocks)
    assert not any("(cid:" in block.chunk.marked_text for block in read.blocks)


def test_a_picture_only_page_between_text_pages_keeps_its_picture() -> None:
    content = merged(pdf_bytes(_FIRST), picture_only_pdf(), pdf_bytes(_THIRD))

    read = read_pdf(content)

    assert read.skipped_pages == ()
    assert [block.chunk.kind for block in read.blocks] == ["paragraph", "drawing", "paragraph"]
    picture = read.blocks[1].chunk
    assert picture.text == ""
    (image,) = picture.images
    assert image.payload.startswith(b"\x89PNG")
    assert [read.blocks[0].chunk.text, read.blocks[2].chunk.text] == [
        "1. Vad heter huvudpersonen?",
        "3. Vilken färg har båten?",
    ]


def test_a_fully_readable_pdf_names_no_skipped_pages() -> None:
    content = pdf_bytes(_FIRST + _BREAK.format(body=_THIRD))

    read = read_pdf(content)

    assert read.skipped_pages == ()
    assert _texts(content) == [
        "1. Vad heter huvudpersonen?",
        "3. Vilken färg har båten?",
    ]


@pytest.mark.parametrize(
    ("pages", "note"),
    [
        ((2,), "Sida 2 importerades inte eftersom texten inte gick att läsa in."),
        (
            (2, 4, 5),
            "Sidorna 2, 4 och 5 importerades inte eftersom texten inte gick att läsa in.",
        ),
        ((3, 7), "Sidorna 3 och 7 importerades inte eftersom texten inte gick att läsa in."),
    ],
    ids=["one-page", "three-pages", "two-pages"],
)
def test_the_skipped_pages_note_names_every_page(pages: tuple[int, ...], note: str) -> None:
    assert skipped_pages_note(pages) == note


def test_a_pdf_that_skipped_a_page_carries_its_note() -> None:
    content = merged(pdf_bytes(_FIRST), pdf_bytes("<p></p>"), pdf_bytes(_THIRD))

    source = PdfPlumberExamChunker().chunk(content=content)

    assert source.notes == ("Sida 2 importerades inte eftersom texten inte gick att läsa in.",)
    assert [chunk.text for chunk in source.chunks] == [
        "1. Vad heter huvudpersonen?",
        "3. Vilken färg har båten?",
    ]


def test_a_fully_readable_pdf_carries_no_note() -> None:
    source = PdfPlumberExamChunker().chunk(content=pdf_bytes(_FIRST + _BREAK.format(body=_THIRD)))

    assert source.notes == ()


@pytest.mark.parametrize(
    "name",
    ["bf26_english_1_unit_test_kap_1_2_med_facit", "metodprov_med_bilder"],
)
def test_the_proof_set_reads_without_skipped_pages(name: str) -> None:
    read = read_pdf((_CORPUS / f"{name}.pdf").read_bytes())

    assert read.skipped_pages == ()
