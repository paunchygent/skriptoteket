"""Pictures, figures and PNG checks shared by the PDF picture tests (TASK-SKRIPT-39-10-02)."""

from __future__ import annotations

import base64
import io

from PIL import Image

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_chunker import (  # noqa: E501
    PdfPlumberExamChunker,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_pdf_test_support import pdf_bytes

PICTURE_SIZE = (120, 80)
PICTURE_BLUE: tuple[int, int, int] = (40, 90, 160)

TRIANGLE_CORNERS = ((20, 130), (180, 130), (100, 20))


def solid_png(width: int, height: int, color: tuple[int, int, int] = PICTURE_BLUE) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, format="PNG")
    return buffer.getvalue()


def picture_tag(payload: bytes, style: str) -> str:
    uri = base64.b64encode(payload).decode("ascii")
    return f'<img src="data:image/png;base64,{uri}" style="{style}">'


def triangle_figure(labels: tuple[str, str, str]) -> str:
    (ax, ay), (bx, by), (cx, cy) = TRIANGLE_CORNERS
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


def pdf_chunks(body: str, *, css: str = "") -> tuple[DocxChunk, ...]:
    return PdfPlumberExamChunker().chunk(content=pdf_bytes(body, css=css)).chunks


def assert_drawing_chunk(chunk: DocxChunk, *, anchor: str) -> bytes:
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


def ink_box(payload: bytes) -> tuple[tuple[int, int, int, int], tuple[int, int]]:
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


def assert_solid_blue(payload: bytes) -> tuple[int, int]:
    """The PNG is solid blue up to an anti-aliased 1 px rim."""
    with Image.open(io.BytesIO(payload)) as shot:
        size = shot.convert("RGB").size
        data = list(shot.convert("RGB").getdata())
    width, height = size
    bad = sum(
        1
        for pixel in data
        if max(abs(part - expected) for part, expected in zip(pixel, PICTURE_BLUE)) > 8
    )
    assert bad <= 2 * (width + height)
    return size
