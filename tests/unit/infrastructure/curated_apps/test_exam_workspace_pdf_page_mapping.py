"""PDF pictures map from page space to their cut through CropBox, rotation and render failure (TASK-SKRIPT-39-10-02)."""  # noqa: E501

from __future__ import annotations

import io

import pdfplumber
import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_chunker import (  # noqa: E501
    PdfPlumberExamChunker,
    PdfPlumberLabelerMarkdown,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_pdf_picture_test_support import (
    PICTURE_BLUE,
    PICTURE_SIZE,
    assert_drawing_chunk,
    assert_solid_blue,
    pdf_chunks,
    picture_tag,
    solid_png,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_pdf_test_support import pdf_bytes

_CROP_PREFIX = "<p>1. Beskriv figuren.</p>"
_CROP_SUFFIX = "<p>2. Fortsätt.</p>"
_CROP_BODY = (
    _CROP_PREFIX
    + f"<p>{picture_tag(solid_png(*PICTURE_SIZE, color=PICTURE_BLUE), 'width:120pt;height:80pt')}</p>"  # noqa: E501
    + _CROP_SUFFIX
)


def _with_cropbox(
    data: bytes,
    lower_left: tuple[float, float],
    upper_right: tuple[float, float],
) -> bytes:
    reader = PdfReader(io.BytesIO(data))
    page = reader.pages[0]
    page.cropbox.lower_left = lower_left
    page.cropbox.upper_right = upper_right
    writer = PdfWriter()
    writer.add_page(page)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def _with_rotation(data: bytes, angle: int) -> bytes:
    reader = PdfReader(io.BytesIO(data))
    reader.pages[0].rotation = angle
    writer = PdfWriter()
    writer.add_page(reader.pages[0])
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def test_cropped_page_picture_is_solid_blue() -> None:
    content = _with_cropbox(pdf_bytes(_CROP_BODY), (50, 50), (550, 800))
    chunks = PdfPlumberExamChunker().chunk(content=content)

    assert [chunk.kind for chunk in chunks] == ["paragraph", "drawing", "paragraph"]
    assert [chunk.text for chunk in chunks if chunk.kind != "drawing"] == [
        "1. Beskriv figuren.",
        "2. Fortsätt.",
    ]
    assert assert_solid_blue(assert_drawing_chunk(chunks[1], anchor="body:0002")) == (
        round(120 * 2.5),
        round(80 * 2.5),
    )


def test_uncropped_page_picture_is_the_same_solid_blue() -> None:
    chunks = pdf_chunks(
        "<p>1. Beskriv figuren.</p>"
        f"<p>{picture_tag(solid_png(*PICTURE_SIZE, color=PICTURE_BLUE), 'width:120pt;height:80pt')}</p>"  # noqa: E501
        "<p>2. Fortsätt.</p>"
    )

    assert [chunk.kind for chunk in chunks] == ["paragraph", "drawing", "paragraph"]
    assert assert_solid_blue(assert_drawing_chunk(chunks[1], anchor="body:0002")) == (
        round(120 * 2.5),
        round(80 * 2.5),
    )


def test_cropbox_cutting_through_a_picture_gives_half_a_solid_picture() -> None:
    data = pdf_bytes(_CROP_BODY)
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        image = pdf.pages[0].images[0]
        middle = (float(image["x0"]) + float(image["x1"])) / 2
    reader = PdfReader(io.BytesIO(data))
    mediabox = reader.pages[0].mediabox
    content = _with_cropbox(
        data, (middle, float(mediabox[1])), (float(mediabox[2]), float(mediabox[3]))
    )
    chunks = PdfPlumberExamChunker().chunk(content=content)

    drawings = [chunk for chunk in chunks if chunk.kind == "drawing"]
    assert len(drawings) == 1
    payload = assert_drawing_chunk(drawings[0], anchor=drawings[0].anchor)
    width, height = assert_solid_blue(payload)
    assert abs(width - round(120 * 2.5) / 2) <= 4
    assert abs(height - round(80 * 2.5)) <= 2


def test_rotated_page_picture_becomes_a_named_missing_picture() -> None:
    content = _with_rotation(pdf_bytes(_CROP_BODY), 90)
    chunks = PdfPlumberExamChunker().chunk(content=content)

    joined = "".join(chunk.text for chunk in chunks if chunk.kind != "drawing")
    assert "Beskriv" in joined.replace(" ", "")
    assert "Fortsätt" in joined.replace(" ", "")
    drawings = [chunk for chunk in chunks if chunk.kind == "drawing"]
    assert len(drawings) == 1
    assert drawings[0].images == ()
    assert [missing.reference for missing in drawings[0].missing_images] == ["PDF-sida 1: bild"]


def test_a_picture_that_cannot_be_rendered_stays_as_a_named_missing_picture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
        exam_workspace_pdf_pictures,
    )

    def failing(pdf: bytes, *, scale: float, pages: object) -> tuple[Image.Image, ...]:
        raise RuntimeError("pdfium failed")

    monkeypatch.setattr(exam_workspace_pdf_pictures, "rasterize_pdf_pages", failing)
    content = pdf_bytes(
        "<p>Fråga 1. Titta på bilden.</p>"
        f"<p>{picture_tag(solid_png(*PICTURE_SIZE), 'width:120pt;height:80pt')}</p>"
        "<p>Fråga 2. Gå vidare.</p>"
    )

    chunks = PdfPlumberExamChunker().chunk(content=content)
    source = PdfPlumberLabelerMarkdown().source(content=content)

    drawing = chunks[1]
    assert (drawing.kind, drawing.images) == ("drawing", ())
    assert [missing.reference for missing in drawing.missing_images] == ["PDF-sida 1: bild"]
    assert source.images == {}
    assert source.unavailable == {"body:0002": "PDF-sida 1: bild"}
