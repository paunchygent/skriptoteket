"""PDF pictures and drawn figures land in their questions (TASK-SKRIPT-39-10-02)."""

from __future__ import annotations

import base64
import io

import pytest
from PIL import Image

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_chunker import (  # noqa: E501
    PdfPlumberExamChunker,
    PdfPlumberLabelerMarkdown,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_pdf_test_support import pdf_bytes

_PICTURE_SIZE = (120, 80)
_PICTURE_ASPECT = 3 / 2
_PICTURE_TOLERANCE = 0.05

_TRIANGLE_CORNERS = ((20, 130), (180, 130), (100, 20))
# Union of the triangle corners and the label anchors below: x 20..180, y 12..144.
_TRIANGLE_ASPECT = 160 / 132
_GENEROUS_CUT_TOLERANCE = 0.15
_MIN_CUT_MARGIN_PX = 3

_ANSWER_LINES_SVG = (
    '<svg width="300" height="60" xmlns="http://www.w3.org/2000/svg">'
    '<line x1="0" y1="10" x2="300" y2="10" stroke="black" stroke-width="1"/>'
    '<line x1="0" y1="35" x2="300" y2="35" stroke="black" stroke-width="1"/>'
    '<line x1="0" y1="60" x2="300" y2="60" stroke="black" stroke-width="1"/>'
    "</svg>"
)


def _solid_png(width: int, height: int, color: tuple[int, int, int] = (40, 90, 160)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, format="PNG")
    return buffer.getvalue()


def _picture_tag(payload: bytes, style: str) -> str:
    uri = base64.b64encode(payload).decode("ascii")
    return f'<img src="data:image/png;base64,{uri}" style="{style}">'


def _triangle_figure(labels: tuple[str, str, str]) -> str:
    (ax, ay), (bx, by), (cx, cy) = _TRIANGLE_CORNERS
    first, second, third = labels
    return (
        '<svg width="200" height="150" viewBox="0 0 200 150" '
        'xmlns="http://www.w3.org/2000/svg">'
        f'<polygon points="{ax},{ay} {bx},{by} {cx},{cy}" fill="none" '
        'stroke="black" stroke-width="2"/>'
        f'<text x="{ax}" y="{ay + 14}" text-anchor="middle" font-size="12">{first}</text>'
        f'<text x="{bx}" y="{by + 14}" text-anchor="middle" font-size="12">{second}</text>'
        f'<text x="{cx}" y="{cy - 8}" text-anchor="middle" font-size="12">{third}</text>'
        "</svg>"
    )


def _chunks(body: str, *, css: str = "") -> tuple[DocxChunk, ...]:
    return PdfPlumberExamChunker().chunk(content=pdf_bytes(body, css=css))


def _assert_drawing_chunk(chunk: DocxChunk, *, anchor: str) -> bytes:
    assert chunk.anchor == anchor
    assert chunk.kind == "drawing"
    assert chunk.text == ""
    assert chunk.marked_text == ""
    (image,) = chunk.images
    assert image.media_type == "image/png"
    assert image.payload.startswith(b"\x89PNG")
    with Image.open(io.BytesIO(image.payload)) as shot:
        assert (image.width, image.height) == shot.size
    return image.payload


def _assert_picture_aspect(payload: bytes) -> None:
    with Image.open(io.BytesIO(payload)) as picture:
        aspect = picture.size[0] / picture.size[1]
    assert abs(aspect - _PICTURE_ASPECT) / _PICTURE_ASPECT <= _PICTURE_TOLERANCE


def _ink_box(payload: bytes) -> tuple[tuple[int, int, int, int], tuple[int, int]]:
    """Bounding box of non-white pixels; white means every channel >= 200."""
    with Image.open(io.BytesIO(payload)) as shot:
        size = shot.convert("RGB").size
        data = list(shot.convert("RGB").getdata())
    width, height = size
    ink = [(x, y) for y in range(height) for x in range(width) if min(data[y * width + x]) < 200]
    assert ink, "the drawing PNG holds no ink"
    left = min(x for x, _ in ink)
    right = max(x for x, _ in ink)
    top = min(y for _, y in ink)
    bottom = max(y for _, y in ink)
    return (left, top, right, bottom), size


def _assert_generous_cut(payload: bytes, *, expected_aspect: float) -> None:
    (left, top, right, bottom), (width, height) = _ink_box(payload)
    assert left >= _MIN_CUT_MARGIN_PX
    assert top >= _MIN_CUT_MARGIN_PX
    assert width - 1 - right >= _MIN_CUT_MARGIN_PX
    assert height - 1 - bottom >= _MIN_CUT_MARGIN_PX
    ink_aspect = (right - left + 1) / (bottom - top + 1)
    assert abs(ink_aspect - expected_aspect) / expected_aspect <= _GENEROUS_CUT_TOLERANCE


def test_embedded_picture_between_questions_becomes_one_drawing_chunk_between_them() -> None:  # noqa: E501
    payload = _solid_png(*_PICTURE_SIZE)
    chunks = _chunks(
        "<p>Fråga 1. Titta på bilden.</p>"
        f"<p>{_picture_tag(payload, 'width:120pt;height:80pt')}</p>"
        "<p>Fråga 2. Gå vidare.</p>"
    )

    assert [chunk.kind for chunk in chunks] == ["paragraph", "drawing", "paragraph"]
    assert [chunk.text for chunk in chunks] == [
        "Fråga 1. Titta på bilden.",
        "",
        "Fråga 2. Gå vidare.",
    ]
    assert [chunk.anchor for chunk in chunks] == ["body:0001", "body:0002", "body:0003"]
    _assert_picture_aspect(_assert_drawing_chunk(chunks[1], anchor="body:0002"))


def test_drawn_triangle_with_labels_becomes_one_generous_drawing_chunk() -> None:
    chunks = _chunks(
        "<p>Fråga 1. Beskriv triangeln med hörnen.</p>"
        f"<p>{_triangle_figure(('A', 'B', 'C'))}</p>"
        "<p>Fråga 2. Gå vidare.</p>"
    )

    assert [chunk.kind for chunk in chunks] == ["paragraph", "drawing", "paragraph"]
    assert [chunk.anchor for chunk in chunks] == ["body:0001", "body:0002", "body:0003"]
    payload = _assert_drawing_chunk(chunks[1], anchor="body:0002")
    _assert_generous_cut(payload, expected_aspect=_TRIANGLE_ASPECT)


def test_figure_labels_are_not_emitted_as_text() -> None:
    labels = ("A", "B", "C")
    chunks = _chunks(
        "<p>Fråga 1. Beskriv triangeln med hörnen.</p>"
        f"<p>{_triangle_figure(labels)}</p>"
        "<p>Fråga 2. Gå vidare.</p>"
    )

    texts = [chunk.text for chunk in chunks if chunk.kind != "drawing"]
    assert texts == ["Fråga 1. Beskriv triangeln med hörnen.", "Fråga 2. Gå vidare."]
    words = {word for text in texts for word in text.split()}
    assert not (set(labels) & words)


def test_drawn_answer_lines_under_svar_give_no_drawing_chunk() -> None:
    chunks = _chunks(f"<p>Svar:</p><p>{_ANSWER_LINES_SVG}</p>")

    assert all(chunk.kind != "drawing" for chunk in chunks)
    assert "Svar:" in [chunk.text for chunk in chunks]


def test_two_drawn_figures_separated_by_a_paragraph_give_two_drawing_chunks_in_order() -> None:  # noqa: E501
    chunks = _chunks(
        "<p>Fråga 1. Beskriv den första triangeln.</p>"
        f"<p>{_triangle_figure(('A', 'B', 'C'))}</p>"
        "<p>Fråga 2. Jämför med nästa triangel.</p>"
        f"<p>{_triangle_figure(('D', 'E', 'F'))}</p>"
        "<p>Fråga 3. Gå vidare.</p>"
    )

    assert [chunk.kind for chunk in chunks] == [
        "paragraph",
        "drawing",
        "paragraph",
        "drawing",
        "paragraph",
    ]
    assert [chunk.anchor for chunk in chunks] == [f"body:{index:04d}" for index in range(1, 6)]
    assert chunks[2].text == "Fråga 2. Jämför med nästa triangel."
    first = _assert_drawing_chunk(chunks[1], anchor="body:0002")
    second = _assert_drawing_chunk(chunks[3], anchor="body:0004")
    assert first != second


def test_labeler_source_carries_each_drawing_png_in_images_with_empty_markdown() -> None:
    payload = _solid_png(*_PICTURE_SIZE)
    content = pdf_bytes(
        "<p>Fråga 1. Titta på bilden.</p>"
        f"<p>{_picture_tag(payload, 'width:120pt;height:80pt')}</p>"
        "<p>Fråga 2. Beskriv triangeln med hörnen.</p>"
        f"<p>{_triangle_figure(('A', 'B', 'C'))}</p>"
        "<p>Fråga 3. Gå vidare.</p>"
    )

    chunks = PdfPlumberExamChunker().chunk(content=content)
    source = PdfPlumberLabelerMarkdown().source(content=content)

    drawings = [chunk for chunk in chunks if chunk.kind == "drawing"]
    assert len(drawings) == 2
    assert [chunk.anchor for chunk in source.chunks] == [chunk.anchor for chunk in chunks]
    for chunk in drawings:
        (image,) = chunk.images
        assert chunk.marked_text == ""
        assert source.images[chunk.anchor] == image.payload
    for chunk in source.chunks:
        if chunk.kind != "drawing":
            assert chunk.marked_text
            assert chunk.anchor not in source.images
    assert set(source.images) == {chunk.anchor for chunk in drawings}


def test_picture_only_pdf_is_a_validation_error() -> None:
    payload = _solid_png(*_PICTURE_SIZE)
    content = pdf_bytes(f"<p>{_picture_tag(payload, 'width:120pt;height:80pt')}</p>")

    with pytest.raises(DomainError) as raised:
        PdfPlumberExamChunker().chunk(content=content)

    assert raised.value.code is ErrorCode.VALIDATION_ERROR
    assert raised.value.message == "PDF-filen saknar läsbart innehåll."


def test_repeated_logo_is_dropped_while_a_body_picture_is_kept() -> None:
    logo = _solid_png(60, 20, color=(200, 30, 30))
    body_picture = _solid_png(*_PICTURE_SIZE)
    content = pdf_bytes(
        '<div style="position: fixed; top: -50pt; left: 0">'
        f"{_picture_tag(logo, 'height:24pt')}</div>"
        "<p>Fråga 1. Första sidan.</p>"
        '<p style="page-break-before: always">Fråga 2. Andra sidan.</p>'
        f"<p>{_picture_tag(body_picture, 'width:120pt;height:80pt')}</p>"
        '<p style="page-break-before: always">Fråga 3. Tredje sidan.</p>'
    )

    chunks = PdfPlumberExamChunker().chunk(content=content)

    assert [chunk.kind for chunk in chunks] == [
        "paragraph",
        "paragraph",
        "drawing",
        "paragraph",
    ]
    assert [chunk.text for chunk in chunks] == [
        "Fråga 1. Första sidan.",
        "Fråga 2. Andra sidan.",
        "",
        "Fråga 3. Tredje sidan.",
    ]
    _assert_picture_aspect(_assert_drawing_chunk(chunks[2], anchor="body:0003"))


def test_empty_bordered_table_becomes_one_drawing_chunk_and_no_table_chunk() -> None:
    chunks = _chunks(
        "<p>Före tabellen.</p>"
        "<table><tr><td></td><td></td><td></td></tr>"
        "<tr><td></td><td></td><td></td></tr>"
        "<tr><td></td><td></td><td></td></tr></table>"
        "<p>Efter tabellen.</p>",
        css="table { border-collapse: collapse; } td { border: 1px solid black; "
        "width: 40pt; height: 40pt; }",
    )

    assert [chunk.kind for chunk in chunks] == ["paragraph", "drawing", "paragraph"]
    assert [chunk.text for chunk in chunks] == ["Före tabellen.", "", "Efter tabellen."]
    _assert_drawing_chunk(chunks[1], anchor="body:0002")


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
        f"<p>{_picture_tag(_solid_png(*_PICTURE_SIZE), 'width:120pt;height:80pt')}</p>"
        "<p>Fråga 2. Gå vidare.</p>"
    )

    chunks = PdfPlumberExamChunker().chunk(content=content)
    source = PdfPlumberLabelerMarkdown().source(content=content)

    drawing = chunks[1]
    assert (drawing.kind, drawing.images) == ("drawing", ())
    assert [missing.reference for missing in drawing.missing_images] == ["PDF-sida 1: bild"]
    assert source.images == {}
    assert source.unavailable == {"body:0002": "PDF-sida 1: bild"}
