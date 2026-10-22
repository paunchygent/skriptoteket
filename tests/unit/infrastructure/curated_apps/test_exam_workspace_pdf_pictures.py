"""PDF pictures and drawn figures land in their questions (TASK-SKRIPT-39-10-02)."""

from __future__ import annotations

import base64
import io

import pdfplumber
import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter

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
# The triangle on its own, without its outside labels: x 20..180, y 20..130.
_TRIANGLE_ONLY_ASPECT = 160 / 110
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


def test_drawn_triangle_with_outside_labels_keeps_a_generous_triangle_only_cut() -> None:
    chunks = _chunks(
        "<p>Fråga 1. Beskriv triangeln med hörnen.</p>"
        f"<p>{_triangle_figure(('A', 'B', 'C'))}</p>"
        "<p>Fråga 2. Gå vidare.</p>"
    )

    assert [chunk.kind for chunk in chunks] == [
        "paragraph",
        "paragraph",
        "drawing",
        "paragraph",
        "paragraph",
    ]
    assert [chunk.anchor for chunk in chunks] == [f"body:{index:04d}" for index in range(1, 6)]
    payload = _assert_drawing_chunk(chunks[2], anchor="body:0003")
    _assert_generous_cut(payload, expected_aspect=_TRIANGLE_ONLY_ASPECT)


def test_triangle_labels_outside_the_outline_are_read_as_text() -> None:
    labels = ("A", "B", "C")
    chunks = _chunks(
        "<p>Fråga 1. Beskriv triangeln med hörnen.</p>"
        f"<p>{_triangle_figure(labels)}</p>"
        "<p>Fråga 2. Gå vidare.</p>"
    )

    texts = [chunk.text for chunk in chunks if chunk.kind != "drawing"]
    joined = " ".join(texts)
    assert "Fråga 1. Beskriv triangeln med hörnen." in joined
    assert "Fråga 2. Gå vidare." in joined
    for label in labels:
        assert label in joined.split()


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
        "paragraph",
        "drawing",
        "paragraph",
        "paragraph",
        "paragraph",
        "drawing",
        "paragraph",
        "paragraph",
    ]
    assert [chunk.anchor for chunk in chunks] == [f"body:{index:04d}" for index in range(1, 10)]
    assert chunks[4].text == "Fråga 2. Jämför med nästa triangel."
    first = _assert_drawing_chunk(chunks[2], anchor="body:0003")
    second = _assert_drawing_chunk(chunks[6], anchor="body:0007")
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


_CROP_PREFIX = "<p>1. Beskriv figuren.</p>"
_CROP_SUFFIX = "<p>2. Fortsätt.</p>"
_CROP_BLUE: tuple[int, int, int] = (40, 90, 160)
_CROP_BODY = (
    _CROP_PREFIX
    + f"<p>{_picture_tag(_solid_png(*_PICTURE_SIZE, color=_CROP_BLUE), 'width:120pt;height:80pt')}</p>"  # noqa: E501
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


def _assert_solid_blue(payload: bytes) -> tuple[int, int]:
    """The PNG is solid blue up to an anti-aliased 1 px rim."""
    with Image.open(io.BytesIO(payload)) as shot:
        size = shot.convert("RGB").size
        data = list(shot.convert("RGB").getdata())
    width, height = size
    bad = sum(
        1
        for pixel in data
        if max(abs(part - expected) for part, expected in zip(pixel, _CROP_BLUE)) > 8
    )
    assert bad <= 2 * (width + height)
    return size


def test_cropped_page_picture_is_solid_blue() -> None:
    content = _with_cropbox(pdf_bytes(_CROP_BODY), (50, 50), (550, 800))
    chunks = PdfPlumberExamChunker().chunk(content=content)

    assert [chunk.kind for chunk in chunks] == ["paragraph", "drawing", "paragraph"]
    assert [chunk.text for chunk in chunks if chunk.kind != "drawing"] == [
        "1. Beskriv figuren.",
        "2. Fortsätt.",
    ]
    assert _assert_solid_blue(_assert_drawing_chunk(chunks[1], anchor="body:0002")) == (
        round(120 * 2.5),
        round(80 * 2.5),
    )


def test_uncropped_page_picture_is_the_same_solid_blue() -> None:
    chunks = _chunks(
        "<p>1. Beskriv figuren.</p>"
        f"<p>{_picture_tag(_solid_png(*_PICTURE_SIZE, color=_CROP_BLUE), 'width:120pt;height:80pt')}</p>"  # noqa: E501
        "<p>2. Fortsätt.</p>"
    )

    assert [chunk.kind for chunk in chunks] == ["paragraph", "drawing", "paragraph"]
    assert _assert_solid_blue(_assert_drawing_chunk(chunks[1], anchor="body:0002")) == (
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
    payload = _assert_drawing_chunk(drawings[0], anchor=drawings[0].anchor)
    width, height = _assert_solid_blue(payload)
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


def _white_pixels(payload: bytes) -> int:
    """Pixels with every channel at least 250: painted-out text, not anti-aliasing."""
    with Image.open(io.BytesIO(payload)) as shot:
        data = list(shot.convert("RGB").getdata())
    return sum(1 for pixel in data if min(pixel) >= 250)


def test_italic_answer_line_under_a_triangle_stays_text() -> None:
    chunks = _chunks(
        "<p>1. Beskriv figuren.</p>"
        '<svg width="240" height="180"><polygon points="40,130 200,130 120,20" '
        'fill="none" stroke="black"/>'
        '<text x="80" y="145" font-size="11" font-style="italic">Svar: 42 cm</text></svg>'
        "<p>2. Fortsätt.</p>"
    )

    assert [chunk.kind for chunk in chunks] == [
        "paragraph",
        "drawing",
        "paragraph",
        "paragraph",
    ]
    joined = " ".join(chunk.text for chunk in chunks if chunk.kind != "drawing")
    assert "Svar" in joined and "42" in joined
    drawings = [chunk for chunk in chunks if chunk.kind == "drawing"]
    assert len(drawings) == 1
    _assert_generous_cut(
        _assert_drawing_chunk(drawings[0], anchor=drawings[0].anchor),
        expected_aspect=160 / 110,
    )


def test_plain_rectangle_with_dimension_stays_a_figure_and_text() -> None:
    chunks = _chunks(
        "<p>1. Beskriv figuren.</p>"
        '<svg width="240" height="180"><rect x="40" y="30" width="150" height="100" '
        'fill="none" stroke="black"/>'
        '<text x="90" y="150" font-size="12">8 cm</text></svg>'
        "<p>2. Fortsätt.</p>"
    )

    drawings = [chunk for chunk in chunks if chunk.kind == "drawing"]
    assert len(drawings) == 1
    assert drawings[0] is chunks[1]
    joined = " ".join(chunk.text for chunk in chunks if chunk.kind != "drawing")
    assert "8" in joined.split() or ("8" in joined and "cm" in joined)
    _assert_generous_cut(
        _assert_drawing_chunk(drawings[0], anchor=drawings[0].anchor),
        expected_aspect=150 / 100,
    )


def test_chart_keeps_axes_and_reads_tick_and_title_as_text() -> None:
    chunks = _chunks(
        "<p>1. Beskriv figuren.</p>"
        '<svg width="240" height="200">'
        '<polyline points="40,20 40,130 200,130" fill="none" stroke="black"/>'
        '<polyline points="40,120 90,100 140,70 200,40" fill="none" stroke="black"/>'
        '<text x="90" y="143" font-size="12">10</text>'
        '<text x="90" y="164" font-size="12">Tid (sekunder)</text></svg>'
        "<p>2. Fortsätt.</p>"
    )

    drawings = [chunk for chunk in chunks if chunk.kind == "drawing"]
    assert len(drawings) == 1
    rest = chunks[chunks.index(drawings[0]) + 1 :]
    after = [chunk.text for chunk in rest if chunk.kind != "drawing"]
    assert "10" in " ".join(after).split()
    assert "Tid" in " ".join(after) and "sekunder" in " ".join(after)
    _assert_generous_cut(
        _assert_drawing_chunk(drawings[0], anchor=drawings[0].anchor),
        expected_aspect=160 / 110,
    )


def test_large_placed_picture_stays_a_picture() -> None:
    payload = _solid_png(420, 610)
    chunks = _chunks(
        "<p>1. Beskriv figuren.</p>"
        f"<p>{_picture_tag(payload, 'width:420pt;height:610pt')}</p>"
        "<p>2. Fortsätt.</p>"
    )

    drawings = [chunk for chunk in chunks if chunk.kind == "drawing"]
    assert len(drawings) == 1
    assert [chunk.kind for chunk in chunks] == ["paragraph", "drawing", "paragraph"]
    image = _assert_drawing_chunk(drawings[0], anchor=drawings[0].anchor)
    with Image.open(io.BytesIO(image)) as shot:
        aspect = shot.size[0] / shot.size[1]
    assert abs(aspect - 420 / 610) / (420 / 610) <= 0.05


_OVERLAY_SENTENCE = "Texten ligger ovanpå bilden."


def _overlay_body(*, with_sentence: bool) -> str:
    picture = _picture_tag(_solid_png(300, 200, color=_CROP_BLUE), "width:300pt;height:200pt")
    paragraph = (
        f'<p style="position:absolute;top:50pt;left:0">{_OVERLAY_SENTENCE}</p>'
        if with_sentence
        else ""
    )
    return (
        "<p>1. Beskriv figuren.</p>"
        '<div style="position:relative">'
        f"<p>{picture}</p>{paragraph}</div>"
        "<p>2. Fortsätt.</p>"
    )


def test_text_over_a_picture_stays_text_and_paints_white_in_the_cut() -> None:
    chunks = _chunks(_overlay_body(with_sentence=True))

    drawings = [chunk for chunk in chunks if chunk.kind == "drawing"]
    assert len(drawings) == 1
    assert _OVERLAY_SENTENCE in [chunk.text for chunk in chunks if chunk.kind != "drawing"]
    payload = _assert_drawing_chunk(drawings[0], anchor=drawings[0].anchor)
    assert _white_pixels(payload) >= 1000

    control = _chunks(_overlay_body(with_sentence=False))
    control_drawings = [chunk for chunk in control if chunk.kind == "drawing"]
    assert len(control_drawings) == 1
    _assert_solid_blue(
        _assert_drawing_chunk(control_drawings[0], anchor=control_drawings[0].anchor)
    )


def _with_blue_ops(base: bytes, ops: bytes) -> bytes:
    from pypdf.generic import DecodedStreamObject

    reader = PdfReader(io.BytesIO(base))
    writer = PdfWriter()
    page = writer.add_page(reader.pages[0])
    contents = page.get_contents()
    assert contents is not None
    stream = DecodedStreamObject()
    stream.set_data(contents.get_data() + b"\nq 0 0 1 rg " + ops + b" Q\n")
    page.replace_contents(stream)  # type: ignore[arg-type]
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def _two_paragraph_base() -> bytes:
    return pdf_bytes(
        '<p>1. Beskriv rektangeln.</p><div style="height:350pt"></div><p>2. Fortsätt.</p>'
    )


def _assert_centre_blue(payload: bytes) -> None:
    with Image.open(io.BytesIO(payload)) as shot:
        rgb = shot.convert("RGB")
        width, height = rgb.size
        points = [
            (width // 2, height // 2),
            (width // 2 - 10, height // 2),
            (width // 2 + 10, height // 2),
            (width // 2, height // 2 - 10),
            (width // 2, height // 2 + 10),
        ]
        for point in points:
            pixel = rgb.getpixel(point)
            assert isinstance(pixel, tuple)
            assert pixel[2] > 200 and pixel[0] < 80 and pixel[1] < 80, (point, pixel)


def test_two_independent_fills_make_one_solid_blue_figure() -> None:
    content = _with_blue_ops(_two_paragraph_base(), b"100 200 200 80 re f* 100 201 200 79 re f*")
    chunks = PdfPlumberExamChunker().chunk(content=content)

    assert [chunk.kind for chunk in chunks] == ["paragraph", "drawing", "paragraph"]
    drawings = [chunk for chunk in chunks if chunk.kind == "drawing"]
    assert len(drawings) == 1
    _assert_centre_blue(_assert_drawing_chunk(drawings[0], anchor=drawings[0].anchor))


def test_one_compound_evenodd_fill_makes_one_figure() -> None:
    content = _with_blue_ops(_two_paragraph_base(), b"100 200 200 80 re 100 201 200 79 re f*")
    chunks = PdfPlumberExamChunker().chunk(content=content)

    assert [chunk.kind for chunk in chunks] == ["paragraph", "drawing", "paragraph"]
    drawings = [chunk for chunk in chunks if chunk.kind == "drawing"]
    assert len(drawings) == 1
    payload = _assert_drawing_chunk(drawings[0], anchor=drawings[0].anchor)
    _ink_box(payload)


def test_single_fill_makes_one_figure() -> None:
    content = _with_blue_ops(_two_paragraph_base(), b"100 200 200 80 re f*")
    chunks = PdfPlumberExamChunker().chunk(content=content)

    assert [chunk.kind for chunk in chunks] == ["paragraph", "drawing", "paragraph"]
    drawings = [chunk for chunk in chunks if chunk.kind == "drawing"]
    assert len(drawings) == 1
    _assert_centre_blue(_assert_drawing_chunk(drawings[0], anchor=drawings[0].anchor))


def test_fill_only_box_behind_text_is_shading_not_a_picture() -> None:
    chunks = _chunks(
        "<p>1. Läs rutan.</p>"
        '<svg width="240" height="150">'
        '<rect x="40" y="30" width="150" height="100" fill="blue"/>'
        '<text x="70" y="80" font-size="12">Svar: 42</text></svg>'
        "<p>2. Fortsätt.</p>"
    )

    assert all(chunk.kind != "drawing" for chunk in chunks)
    joined = " ".join(chunk.text for chunk in chunks if chunk.kind != "drawing")
    assert "Svar" in joined and "42" in joined


def test_boxed_answer_stays_text_and_interior_paints_white() -> None:
    chunks = _chunks(
        "<p>1. Beskriv figuren.</p>"
        '<svg width="240" height="100" xmlns="http://www.w3.org/2000/svg">'
        '<rect x="20" y="20" width="200" height="60" fill="none" '
        'stroke="black" stroke-width="2"/>'
        '<text x="120" y="55" text-anchor="middle" font-size="14">Svar: 42</text></svg>'
        "<p>2. Fortsätt.</p>"
    )

    drawings = [chunk for chunk in chunks if chunk.kind == "drawing"]
    assert len(drawings) == 1
    joined = " ".join(chunk.text for chunk in chunks if chunk.kind != "drawing")
    assert "Svar" in joined and "42" in joined
    payload = _assert_drawing_chunk(drawings[0], anchor=drawings[0].anchor)
    (left, top, right, bottom), _ = _ink_box(payload)
    with Image.open(io.BytesIO(payload)) as shot:
        data = list(shot.convert("RGB").getdata())
        width, _ = shot.size
    inside = [
        data[y * width + x] for y in range(top + 6, bottom - 5) for x in range(left + 6, right - 5)
    ]
    assert inside
    assert all(min(pixel) >= 250 for pixel in inside)
