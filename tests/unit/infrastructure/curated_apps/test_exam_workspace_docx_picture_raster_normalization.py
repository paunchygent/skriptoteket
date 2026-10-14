"""Word picture raster normalization: format, alpha and metadata handling (TASK-SKRIPT-39-05-09)."""

import io

import pytest
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.opc.packuri import PackURI
from docx.opc.part import Part
from docx.oxml.ns import qn
from PIL import Image, PngImagePlugin

from tests.unit.infrastructure.curated_apps.exam_workspace_docx_picture_support import (
    ALPHA_ROWS,
    chunk_document,
    document_with_picture,
    halves,
    jpeg,
    pixels,
    render_pixels,
    rgba_pixels,
    set_src_rect,
)

pytestmark = pytest.mark.unit


def test_a_readable_bmp_picture_normalizes_to_png_for_chunk_and_renderer() -> None:
    buffer = io.BytesIO()
    Image.new("RGB", (6, 3), (10, 120, 30)).save(buffer, format="BMP")
    document, _, paragraph = document_with_picture(buffer.getvalue())

    (chunk,) = chunk_document(document)

    assert chunk.missing_images == ()
    (image,) = chunk.images
    assert image.media_type == "image/png"
    assert image.payload.startswith(b"\x89PNG\r\n\x1a\n")
    assert (image.width, image.height) == (6, 3)
    assert set(pixels(image.payload)) == {(10, 120, 30)}

    rendered = render_pixels(document, paragraph)
    assert any(
        abs(red - 10) < 40 and abs(green - 120) < 40 and abs(blue - 30) < 40
        for red, green, blue in rendered
    )


def test_an_alpha_tiff_normalizes_to_a_png_that_keeps_the_alpha() -> None:
    buffer = io.BytesIO()
    Image.new("RGBA", (2, 2), (0, 200, 0, 128)).save(buffer, format="TIFF")
    document, _, _ = document_with_picture(buffer.getvalue())

    (chunk,) = chunk_document(document)

    assert chunk.missing_images == ()
    (image,) = chunk.images
    assert image.media_type == "image/png"
    assert rgba_pixels(image.payload) == [(0, 200, 0, 128)] * 4


def test_a_gif_transparency_index_normalizes_to_a_png_that_keeps_the_alpha() -> None:
    image = Image.new("P", (2, 2), 0)
    image.putpalette([0, 255, 0, 255, 0, 0] + [0, 0, 0] * 254)
    image.putdata([0, 1, 1, 0])
    buffer = io.BytesIO()
    image.save(buffer, format="GIF", transparency=1)
    document, _, _ = document_with_picture(buffer.getvalue())

    (chunk,) = chunk_document(document)

    assert chunk.missing_images == ()
    (image,) = chunk.images
    assert image.media_type == "image/png"
    assert rgba_pixels(image.payload) == [
        (0, 255, 0, 255),
        (255, 0, 0, 0),
        (255, 0, 0, 0),
        (0, 255, 0, 255),
    ]


def test_a_malformed_png_part_is_a_named_missing_not_a_broken_image() -> None:
    document, blip, _ = document_with_picture(halves())
    broken = Part(PackURI("/word/media/trasig.png"), "image/png", b"inte en png", None)
    blip.set(qn("r:embed"), document.part.relate_to(broken, RELATIONSHIP_TYPE.IMAGE))

    (chunk,) = chunk_document(document)

    assert chunk.images == ()
    (missing,) = chunk.missing_images
    assert missing.reference == "/word/media/trasig.png"
    assert missing.media_type == "image/png"


@pytest.mark.parametrize(
    ("alias", "extension", "actual", "media_type"),
    [
        ("image/jpg", "jpg", "jpeg", "image/jpeg"),
        ("image/x-png", "png", "png", "image/png"),
        ("image/x-emf", "emf", "png", "image/png"),
    ],
    ids=["jpeg-alias", "png-alias", "raster-with-vector-mime"],
)
def test_an_aliased_mime_reports_the_actual_raster_format(
    alias: str, extension: str, actual: str, media_type: str
) -> None:
    payload = jpeg() if actual == "jpeg" else halves()
    document, blip, _ = document_with_picture(payload)
    part = Part(PackURI(f"/word/media/alias.{extension}"), alias, payload, None)
    blip.set(qn("r:embed"), document.part.relate_to(part, RELATIONSHIP_TYPE.IMAGE))

    (chunk,) = chunk_document(document)

    (image,) = chunk.images
    assert image.payload == payload
    assert image.media_type == media_type


def test_a_crop_transcode_drops_the_source_metadata() -> None:
    image = Image.new("RGB", (200, 100), (0, 0, 255))
    image.paste((255, 0, 0), (0, 0, 100, 100))
    info = PngImagePlugin.PngInfo()
    info.add_text("Secret", "hidden-right-half")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", pnginfo=info)
    document, blip, _ = document_with_picture(buffer.getvalue())
    set_src_rect(blip, r="50000")

    (chunk,) = chunk_document(document)

    (cropped,) = chunk.images
    assert set(pixels(cropped.payload)) == {(255, 0, 0)}
    assert b"Secret" not in cropped.payload
    assert b"hidden-right-half" not in cropped.payload


def test_an_alpha_crop_drops_the_source_metadata_and_keeps_the_alpha() -> None:
    image = Image.new("RGBA", (4, 2))
    image.putdata([pixel for row in ALPHA_ROWS for pixel in row])
    info = PngImagePlugin.PngInfo()
    info.add_text("Secret", "transparent-left-half")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", pnginfo=info)
    document, blip, _ = document_with_picture(buffer.getvalue())
    set_src_rect(blip, r="50000")

    (chunk,) = chunk_document(document)

    (cropped,) = chunk.images
    assert rgba_pixels(cropped.payload) == [
        (255, 0, 0, 0),
        (0, 255, 0, 0),
        (0, 0, 0, 0),
        (0, 0, 0, 128),
    ]
    assert b"Secret" not in cropped.payload
    assert b"transparent-left-half" not in cropped.payload


def test_an_animated_png_flattens_to_its_first_frame() -> None:
    first = Image.new("RGB", (4, 2), (255, 0, 0))
    second = Image.new("RGB", (4, 2), (0, 0, 255))
    buffer = io.BytesIO()
    first.save(buffer, format="PNG", save_all=True, append_images=[second], duration=100, loop=0)
    document, _, _ = document_with_picture(buffer.getvalue())

    (chunk,) = chunk_document(document)

    (image,) = chunk.images
    assert image.media_type == "image/png"
    with Image.open(io.BytesIO(image.payload)) as decoded:
        assert int(getattr(decoded, "n_frames", 1)) == 1
    assert set(pixels(image.payload)) == {(255, 0, 0)}
