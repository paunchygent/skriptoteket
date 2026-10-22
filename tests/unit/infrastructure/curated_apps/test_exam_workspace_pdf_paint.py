"""PDF paint decides what is a picture: whiteout, fill operations, shading and boxes (TASK-SKRIPT-39-10-02)."""  # noqa: E501

from __future__ import annotations

import io

from PIL import Image
from pypdf import PdfReader, PdfWriter

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_chunker import (  # noqa: E501
    PdfPlumberExamChunker,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_pdf_picture_test_support import (
    PICTURE_BLUE,
    assert_drawing_chunk,
    assert_solid_blue,
    ink_box,
    pdf_chunks,
    picture_tag,
    solid_png,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_pdf_test_support import pdf_bytes

_OVERLAY_SENTENCE = "Texten ligger ovanpå bilden."


def _white_pixels(payload: bytes) -> int:
    """Pixels with every channel at least 250: painted-out text, not anti-aliasing."""
    with Image.open(io.BytesIO(payload)) as shot:
        data = list(shot.convert("RGB").getdata())
    return sum(1 for pixel in data if min(pixel) >= 250)


def _overlay_body(*, with_sentence: bool) -> str:
    picture = picture_tag(solid_png(300, 200, color=PICTURE_BLUE), "width:300pt;height:200pt")
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
    chunks = pdf_chunks(_overlay_body(with_sentence=True))

    drawings = [chunk for chunk in chunks if chunk.kind == "drawing"]
    assert len(drawings) == 1
    assert _OVERLAY_SENTENCE in [chunk.text for chunk in chunks if chunk.kind != "drawing"]
    payload = assert_drawing_chunk(drawings[0], anchor=drawings[0].anchor)
    assert _white_pixels(payload) >= 1000

    control = pdf_chunks(_overlay_body(with_sentence=False))
    control_drawings = [chunk for chunk in control if chunk.kind == "drawing"]
    assert len(control_drawings) == 1
    assert_solid_blue(assert_drawing_chunk(control_drawings[0], anchor=control_drawings[0].anchor))


def _with_blue_ops(base: bytes, ops: bytes) -> bytes:
    """Append blue fill operations to the first page's own content stream."""
    reader = PdfReader(io.BytesIO(base))
    writer = PdfWriter()
    page = writer.add_page(reader.pages[0])
    contents = page.get_contents()
    assert contents is not None
    contents.set_data(contents.get_data() + b"\nq 0 0 1 rg " + ops + b" Q\n")
    page.replace_contents(contents)
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
    _assert_centre_blue(assert_drawing_chunk(drawings[0], anchor=drawings[0].anchor))


def test_one_compound_evenodd_fill_makes_one_figure() -> None:
    content = _with_blue_ops(_two_paragraph_base(), b"100 200 200 80 re 100 201 200 79 re f*")
    chunks = PdfPlumberExamChunker().chunk(content=content)

    assert [chunk.kind for chunk in chunks] == ["paragraph", "drawing", "paragraph"]
    drawings = [chunk for chunk in chunks if chunk.kind == "drawing"]
    assert len(drawings) == 1
    payload = assert_drawing_chunk(drawings[0], anchor=drawings[0].anchor)
    ink_box(payload)


def test_single_fill_makes_one_figure() -> None:
    content = _with_blue_ops(_two_paragraph_base(), b"100 200 200 80 re f*")
    chunks = PdfPlumberExamChunker().chunk(content=content)

    assert [chunk.kind for chunk in chunks] == ["paragraph", "drawing", "paragraph"]
    drawings = [chunk for chunk in chunks if chunk.kind == "drawing"]
    assert len(drawings) == 1
    _assert_centre_blue(assert_drawing_chunk(drawings[0], anchor=drawings[0].anchor))


def test_fill_only_box_behind_text_is_shading_not_a_picture() -> None:
    chunks = pdf_chunks(
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
    chunks = pdf_chunks(
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
    payload = assert_drawing_chunk(drawings[0], anchor=drawings[0].anchor)
    (left, top, right, bottom), _ = ink_box(payload)
    with Image.open(io.BytesIO(payload)) as shot:
        data = list(shot.convert("RGB").getdata())
        width, _ = shot.size
    inside = [
        data[y * width + x] for y in range(top + 6, bottom - 5) for x in range(left + 6, right - 5)
    ]
    assert inside
    assert all(min(pixel) >= 250 for pixel in inside)
