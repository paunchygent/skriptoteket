"""Fixtures shared by the DOCX picture transform and raster normalization tests."""

from __future__ import annotations

import io

from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from PIL import Image

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_labeler_block_image import (  # noqa: E501
    DocxBlockImageRenderer,
)

# RGBA pixels whose alpha varies: fully transparent colours, a half-transparent colour and
# opaque colours. The hidden RGB values must survive beside the alpha value.
ALPHA_ROWS = [
    [(255, 0, 0, 0), (0, 255, 0, 0), (0, 0, 255, 128), (255, 255, 0, 255)],
    [(0, 0, 0, 0), (0, 0, 0, 128), (10, 20, 30, 0), (40, 50, 60, 255)],
]


def halves() -> bytes:
    """A 200x100 picture with a red left half and a blue right half."""
    image = Image.new("RGB", (200, 100), (0, 0, 255))
    image.paste((255, 0, 0), (0, 0, 100, 100))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def jpeg() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (20, 10), (7, 8, 9)).save(buffer, format="JPEG")
    return buffer.getvalue()


def pixels(payload: bytes) -> list[tuple[int, int, int]]:
    with Image.open(io.BytesIO(payload)) as image:
        raw = image.convert("RGB").tobytes()
    return [(raw[index], raw[index + 1], raw[index + 2]) for index in range(0, len(raw), 3)]


def rgba_png(rows: list[list[tuple[int, int, int, int]]]) -> bytes:
    image = Image.new("RGBA", (len(rows[0]), len(rows)))
    image.putdata([pixel for row in rows for pixel in row])
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def rgba_pixels(payload: bytes) -> list[tuple[int, int, int, int]]:
    with Image.open(io.BytesIO(payload)) as image:
        assert "A" in image.getbands(), f"no alpha channel in mode {image.mode}"
        raw = image.convert("RGBA").tobytes()
    return [
        (raw[index], raw[index + 1], raw[index + 2], raw[index + 3])
        for index in range(0, len(raw), 4)
    ]


def document_with_picture(payload: bytes):
    document = Document()
    document.add_picture(io.BytesIO(payload))
    paragraph = document.element.body.findall(qn("w:p"))[-1]
    blip = next(paragraph.iter(qn("a:blip")))
    return document, blip, paragraph


def save_document(document) -> bytes:
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def chunk_document(document):
    return PythonDocxExamChunker().chunk(content=save_document(document))


def render_pixels(document, paragraph) -> list[tuple[int, int, int]]:
    payload = DocxBlockImageRenderer(document).render(paragraph, anchor="body:0001")
    return pixels(payload)


def set_src_rect(blip, **attributes: str) -> None:
    picture = next(blip.iterancestors(qn("pic:pic")))
    fill = picture.find(qn("pic:blipFill"))
    assert fill is not None
    rendered = " ".join(f'{name}="{value}"' for name, value in attributes.items())
    fill.insert(1, parse_xml(f"<a:srcRect {nsdecls('a')} {rendered}/>"))
