"""Word picture transforms: crop, flip and quarter turns, or a named gate (TASK-SKRIPT-39-05-09)."""

import io

import pytest
from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.opc.packuri import PackURI
from docx.opc.part import Part
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from PIL import Image, PngImagePlugin

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxMissingImage
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_picture import (  # noqa: E501
    picture_from_relationship,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_labeler_block_image import (  # noqa: E501
    DocxBlockImageRenderer,
    LabelerSourceImageUnavailable,
)

pytestmark = pytest.mark.unit

_A, _B, _C, _D = (255, 0, 0), (0, 200, 0), (0, 0, 255), (255, 255, 0)
_E, _F, _G, _H = (255, 0, 255), (0, 255, 255), (128, 64, 32), (9, 18, 27)
_QUARTER_TURNS = [
    pytest.param({"flipH": "1"}, [[_D, _C, _B, _A], [_H, _G, _F, _E]], id="flipH"),
    pytest.param({"flipV": "1"}, [[_E, _F, _G, _H], [_A, _B, _C, _D]], id="flipV"),
    pytest.param({"rot": str(90 * 60000)}, [[_E, _A], [_F, _B], [_G, _C], [_H, _D]], id="rot90"),
    pytest.param({"rot": str(180 * 60000)}, [[_H, _G, _F, _E], [_D, _C, _B, _A]], id="rot180"),
    pytest.param({"rot": str(270 * 60000)}, [[_D, _H], [_C, _G], [_B, _F], [_A, _E]], id="rot270"),
]


def _png(rows: list[list[tuple[int, int, int]]]) -> bytes:
    image = Image.new("RGB", (len(rows[0]), len(rows)))
    image.putdata([pixel for row in rows for pixel in row])
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _checkerboard() -> bytes:
    return _png([[_A, _B, _C, _D], [_E, _F, _G, _H]])


def _halves() -> bytes:
    """A 200x100 picture with a red left half and a blue right half."""
    image = Image.new("RGB", (200, 100), (0, 0, 255))
    image.paste((255, 0, 0), (0, 0, 100, 100))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _jpeg() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (20, 10), (7, 8, 9)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _pixels(payload: bytes) -> list[tuple[int, int, int]]:
    with Image.open(io.BytesIO(payload)) as image:
        raw = image.convert("RGB").tobytes()
    return [(raw[index], raw[index + 1], raw[index + 2]) for index in range(0, len(raw), 3)]


def _document_with_picture(payload: bytes):
    document = Document()
    document.add_picture(io.BytesIO(payload))
    paragraph = document.element.body.findall(qn("w:p"))[-1]
    blip = next(paragraph.iter(qn("a:blip")))
    return document, blip, paragraph


def _save(document) -> bytes:
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _chunk(document):
    return PythonDocxExamChunker().chunk(content=_save(document))


def _render_pixels(document, paragraph) -> list[tuple[int, int, int]]:
    payload = DocxBlockImageRenderer(document).render(paragraph, anchor="body:0001")
    return _pixels(payload)


def _set_src_rect(blip, **attributes: str) -> None:
    picture = next(blip.iterancestors(qn("pic:pic")))
    fill = picture.find(qn("pic:blipFill"))
    assert fill is not None
    rendered = " ".join(f'{name}="{value}"' for name, value in attributes.items())
    fill.insert(1, parse_xml(f"<a:srcRect {nsdecls('a')} {rendered}/>"))


def _set_xfrm(blip, **attributes: str) -> None:
    picture = next(blip.iterancestors(qn("pic:pic")))
    properties = picture.find(qn("pic:spPr"))
    assert properties is not None
    frame = properties.find(qn("a:xfrm"))
    assert frame is not None
    for name, value in attributes.items():
        frame.set(name, value)


def _set_geometry(blip, prst: str) -> None:
    picture = next(blip.iterancestors(qn("pic:pic")))
    properties = picture.find(qn("pic:spPr"))
    assert properties is not None
    geometry = properties.find(qn("a:prstGeom"))
    assert geometry is not None
    geometry.set("prst", prst)


def _vml_xml(payload: bytes, *, style: str, attributes: str = "") -> bytes:
    document = Document()
    part = Part(PackURI("/word/media/vml.png"), "image/png", payload, None)
    rid = document.part.relate_to(part, RELATIONSHIP_TYPE.IMAGE)
    paragraph = document.add_paragraph()
    spacing = f" {attributes}" if attributes else ""
    paragraph.add_run()._r.append(
        parse_xml(
            '<w:pict xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
            ' xmlns:v="urn:schemas-microsoft-com:vml"'
            ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<v:shape style="{style}"><v:imagedata r:id="{rid}"{spacing}/></v:shape></w:pict>'
        )
    )
    return _save(document)


def test_a_cropped_picture_keeps_only_the_visible_half() -> None:
    document, blip, paragraph = _document_with_picture(_halves())
    _set_src_rect(blip, r="50000")

    (chunk,) = _chunk(document)

    assert chunk.missing_images == ()
    (image,) = chunk.images
    assert image.media_type == "image/png"
    assert (image.width, image.height) == (100, 100)
    assert set(_pixels(image.payload)) == {(255, 0, 0)}

    rendered = _render_pixels(document, paragraph)
    assert all(blue <= red + 40 for red, _, blue in rendered)
    assert any(red > blue + 100 for red, _, blue in rendered)


def test_a_non_right_rotation_is_missing_and_the_renderer_refuses_the_block() -> None:
    document, blip, paragraph = _document_with_picture(_halves())
    _set_xfrm(blip, rot=str(45 * 60000))

    (chunk,) = _chunk(document)

    assert chunk.images == ()
    (missing,) = chunk.missing_images
    assert isinstance(missing, DocxMissingImage)
    assert missing.media_type == "image/png"
    assert missing.reference.startswith("/word/media/image")
    assert "rotation som inte är ett kvarts varv" in missing.reference
    with pytest.raises(LabelerSourceImageUnavailable) as raised:
        DocxBlockImageRenderer(document).render(paragraph, anchor="body:0001")
    assert "rotation" in raised.value.reason


@pytest.mark.parametrize(("attributes", "expected"), _QUARTER_TURNS)
def test_flips_and_quarter_turns_turn_the_pixels(attributes: dict[str, str], expected) -> None:
    document, blip, _ = _document_with_picture(_checkerboard())
    _set_xfrm(blip, **attributes)

    (chunk,) = _chunk(document)

    assert chunk.missing_images == ()
    (image,) = chunk.images
    assert image.media_type == "image/png"
    assert (image.width, image.height) == (len(expected[0]), len(expected))
    assert _pixels(image.payload) == [pixel for row in expected for pixel in row]


def test_a_readable_bmp_picture_normalizes_to_png_for_chunk_and_renderer() -> None:
    buffer = io.BytesIO()
    Image.new("RGB", (6, 3), (10, 120, 30)).save(buffer, format="BMP")
    document, _, paragraph = _document_with_picture(buffer.getvalue())

    (chunk,) = _chunk(document)

    assert chunk.missing_images == ()
    (image,) = chunk.images
    assert image.media_type == "image/png"
    assert image.payload.startswith(b"\x89PNG\r\n\x1a\n")
    assert (image.width, image.height) == (6, 3)
    assert set(_pixels(image.payload)) == {(10, 120, 30)}

    rendered = _render_pixels(document, paragraph)
    assert any(
        abs(red - 10) < 40 and abs(green - 120) < 40 and abs(blue - 30) < 40
        for red, green, blue in rendered
    )


def test_a_noop_transform_keeps_png_and_jpeg_bytes_exact() -> None:
    png = _halves()
    jpeg_buffer = io.BytesIO()
    Image.new("RGB", (20, 10), (7, 8, 9)).save(jpeg_buffer, format="JPEG")
    jpeg = jpeg_buffer.getvalue()
    document = Document()
    document.add_picture(io.BytesIO(png))
    document.paragraphs[0].add_run().add_picture(io.BytesIO(jpeg))
    for blip in document.element.body.iter(qn("a:blip")):
        _set_src_rect(blip, l="0", t="0", r="0", b="0")
        _set_xfrm(blip, rot="0", flipH="0", flipV="0")

    (chunk,) = _chunk(document)

    assert chunk.missing_images == ()
    assert [image.payload for image in chunk.images] == [png, jpeg]
    assert [image.media_type for image in chunk.images] == ["image/png", "image/jpeg"]


@pytest.mark.parametrize(
    "attributes",
    [{"l": "abc"}, {"l": "-1"}, {"l": "60000", "r": "60000"}],
    ids=["unparsable", "negative", "empty"],
)
def test_an_invalid_crop_is_a_named_missing(attributes: dict[str, str]) -> None:
    document, blip, _ = _document_with_picture(_halves())
    _set_src_rect(blip, **attributes)

    (chunk,) = _chunk(document)

    assert chunk.images == ()
    (missing,) = chunk.missing_images
    assert missing.media_type == "image/png"
    assert "beskärning" in missing.reference


def test_an_invalid_flip_is_a_named_missing() -> None:
    document, blip, _ = _document_with_picture(_halves())
    _set_xfrm(blip, flipH="maybe")

    (chunk,) = _chunk(document)

    assert chunk.images == ()
    (missing,) = chunk.missing_images
    assert "spegling" in missing.reference


def test_a_non_rectangular_shape_is_a_named_missing() -> None:
    document, blip, _ = _document_with_picture(_halves())
    _set_geometry(blip, "ellipse")

    (chunk,) = _chunk(document)

    assert chunk.images == ()
    (missing,) = chunk.missing_images
    assert "rektangel" in missing.reference


def test_an_image_effect_is_a_named_missing() -> None:
    document, blip, _ = _document_with_picture(_halves())
    blip.append(parse_xml(f'<a:lum {nsdecls("a")} bright="20000" contrast="0"/>'))

    (chunk,) = _chunk(document)

    assert chunk.images == ()
    (missing,) = chunk.missing_images
    assert "bildeffekt" in missing.reference


@pytest.mark.parametrize(
    ("style", "attributes"),
    [
        ("width:200pt;height:100pt", ""),
        ("width:200pt;height:100pt", 'cropleft="0"'),
        ("width:200pt;height:100pt;rotation:0", ""),
        ("width:200pt;height:100pt", 'grayscale="f"'),
    ],
    ids=["plain", "zero-crop", "zero-rotation", "false-effect"],
)
def test_a_vml_picture_without_transforms_stays_byte_exact(style: str, attributes: str) -> None:
    payload = _halves()
    document = Document(io.BytesIO(_vml_xml(payload, style=style, attributes=attributes)))

    (chunk,) = _chunk(document)

    assert chunk.missing_images == ()
    (image,) = chunk.images
    assert image.payload == payload
    assert image.media_type == "image/png"


@pytest.mark.parametrize(
    ("style", "attributes", "note"),
    [
        ("width:10pt;height:10pt", 'cropleft="0.1"', "beskärning"),
        ("width:10pt;height:10pt;rotation:45", "", "rotation"),
        ("width:10pt;height:10pt;flip:x", "", "rotation"),
    ],
    ids=["crop", "rotation", "flip"],
)
def test_a_vml_transform_is_a_named_missing(style: str, attributes: str, note: str) -> None:
    content = _vml_xml(_halves(), style=style, attributes=attributes)

    (chunk,) = PythonDocxExamChunker().chunk(content=content)

    assert chunk.images == ()
    (missing,) = chunk.missing_images
    assert missing.media_type == "image/png"
    assert note in missing.reference


def test_a_missing_relationship_keeps_a_descriptive_name() -> None:
    missing = picture_from_relationship(Document(), None)

    assert isinstance(missing, DocxMissingImage)
    assert missing.reference == "bild utan inbäddad relation"
    assert missing.media_type == "application/octet-stream"


def test_a_drawing_without_an_embedded_relationship_is_a_named_missing() -> None:
    document, blip, _ = _document_with_picture(_halves())
    blip.attrib.pop(qn("r:embed"))

    (chunk,) = _chunk(document)

    assert chunk.images == ()
    (missing,) = chunk.missing_images
    assert missing.reference == "bild utan inbäddad relation"
    assert missing.media_type == "application/octet-stream"


def test_a_malformed_png_part_is_a_named_missing_not_a_broken_image() -> None:
    document, blip, _ = _document_with_picture(_halves())
    broken = Part(PackURI("/word/media/trasig.png"), "image/png", b"inte en png", None)
    blip.set(qn("r:embed"), document.part.relate_to(broken, RELATIONSHIP_TYPE.IMAGE))

    (chunk,) = _chunk(document)

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
    payload = _jpeg() if actual == "jpeg" else _halves()
    document, blip, _ = _document_with_picture(payload)
    part = Part(PackURI(f"/word/media/alias.{extension}"), alias, payload, None)
    blip.set(qn("r:embed"), document.part.relate_to(part, RELATIONSHIP_TYPE.IMAGE))

    (chunk,) = _chunk(document)

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
    document, blip, _ = _document_with_picture(buffer.getvalue())
    _set_src_rect(blip, r="50000")

    (chunk,) = _chunk(document)

    (cropped,) = chunk.images
    assert set(_pixels(cropped.payload)) == {(255, 0, 0)}
    assert b"Secret" not in cropped.payload
    assert b"hidden-right-half" not in cropped.payload


def test_an_animated_png_flattens_to_its_first_frame() -> None:
    first = Image.new("RGB", (4, 2), (255, 0, 0))
    second = Image.new("RGB", (4, 2), (0, 0, 255))
    buffer = io.BytesIO()
    first.save(buffer, format="PNG", save_all=True, append_images=[second], duration=100, loop=0)
    document, _, _ = _document_with_picture(buffer.getvalue())

    (chunk,) = _chunk(document)

    (image,) = chunk.images
    assert image.media_type == "image/png"
    with Image.open(io.BytesIO(image.payload)) as decoded:
        assert int(getattr(decoded, "n_frames", 1)) == 1
    assert set(_pixels(image.payload)) == {(255, 0, 0)}
