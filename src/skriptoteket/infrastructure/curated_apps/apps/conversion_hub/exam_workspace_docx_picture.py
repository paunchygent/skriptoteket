"""Normalize one embedded Word picture before the native build or the labeler sees it.

Purpose:
    The chunker extracts pictures for the native exam and the labeler block renderer draws
    them for the item-type model. Both must see the same picture: byte-exact PNG/JPEG when
    the source has no transform, a re-encoded PNG for other readable raster media, and a
    named ``DocxMissingImage`` when a Word transform cannot be reproduced faithfully. A
    crop, flip or rotation that cannot be applied must never fall back to the untransformed
    bitmap, because that would show content the source hides.

Relationships:
    ``PythonDocxExamChunker`` calls ``picture_from_relationship`` for every ``a:blip`` and
    ``v:imagedata`` node; ``DocxBlockImageRenderer`` calls it for the same nodes and raises
    ``_Unrenderable`` when it returns a missing picture.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Literal

from docx.document import Document as DocxDocument
from docx.oxml.ns import qn
from docx.oxml.xmlchemy import BaseOxmlElement
from PIL import Image

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxImage, DocxMissingImage
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_image_readability import (
    probe_image_payload,
)

_PIC = qn("pic:pic")
_BLIP_FILL = qn("pic:blipFill")
_SP_PR = qn("pic:spPr")
_EXT_LST = qn("a:extLst")
_SRC_RECT = qn("a:srcRect")
_TILE = qn("a:tile")
_XFRM = qn("a:xfrm")
_PRST_GEOM = qn("a:prstGeom")
_CUST_GEOM = qn("a:custGeom")
_SHAPE_EFFECTS = tuple(qn(tag) for tag in ("a:effectLst", "a:effectDag", "a:scene3d", "a:sp3d"))
_V_IMAGEDATA = "{urn:schemas-microsoft-com:vml}imagedata"
_BYTE_EXACT_MEDIA_TYPES: dict[str, Literal["image/png", "image/jpeg"]] = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
}
# Pillow cannot read these vectors; a PNG payload under such a media type must stay
# missing rather than be decoded as a raster.
_VML_CROP_ATTRIBUTES = ("cropleft", "croptop", "cropright", "cropbottom")
_VML_EFFECT_ATTRIBUTES = (
    "gain", "blacklevel", "gamma", "bilevel", "grayscale", "chromakey", "emboss", "shadow",
)  # fmt: skip
_QUARTER_TURN = 5_400_000
_FULL_TURN = 21_600_000
_CROP_INVALID = "ogiltig beskärning kan inte återges"
_CROP_EMPTY = "tom beskärning kan inte återges"
_ROTATION_INVALID = "ogiltig rotation kan inte återges"
_ROTATION_NOT_QUARTER = "rotation som inte är ett kvarts varv kan inte återges"
_FLIP_INVALID = "ogiltig spegling kan inte återges"
_SHAPE_GEOMETRY = "bildform som inte är en rektangel kan inte återges"
_CUSTOM_GEOMETRY = "egen bildform kan inte återges"
_IMAGE_EFFECT = "bildeffekt kan inte återges"
_TILED_IMAGE = "mönsterupprepad bild kan inte återges"
_VML_CROP = "beskärning kan inte återges"
_VML_TRANSFORM = "rotation eller spegling kan inte återges"


@dataclass(frozen=True)
class _Transform:
    """One picture's reproducible Word transform: crop percentages and quarter turns."""

    crop: tuple[int, int, int, int] | None = None
    flip_h: bool = False
    flip_v: bool = False
    quarter_turns: int = 0

    @property
    def is_noop(self) -> bool:
        return self.crop is None and not self.flip_h and not self.flip_v and self.quarter_turns == 0


@dataclass(frozen=True)
class _Raster:
    """A payload's actual Pillow format and first-frame size, not its declared MIME."""

    format: str
    width: int
    height: int
    animated: bool


def picture_from_relationship(
    document: DocxDocument, rid: str | None, *, element: BaseOxmlElement | None = None
) -> DocxImage | DocxMissingImage:
    """The picture behind one relationship id, normalized to PNG/JPEG or a named missing.

    ``element`` is the exact ``a:blip`` or ``v:imagedata`` node the id comes from, so the
    nearest picture shape's crop, flip and quarter-turn can be applied. The payload's
    actual Pillow format decides what the picture is: readable static PNG/JPEG keep their
    exact payload and report their true media type, whatever MIME the package declares;
    other readable raster media (GIF, BMP, TIFF, ...) and any transformed or animated
    picture decode their first frame into a metadata-free PNG. A missing relationship, a
    malformed or undecodable payload, or any transform this common
    normalizer cannot reproduce becomes ``DocxMissingImage`` whose reference names the part
    and, for a transform, the reason, so the picture never vanishes silently and its hidden
    area is never shown.
    """
    if rid is None:
        return DocxMissingImage(
            reference="bild utan inbäddad relation", media_type="application/octet-stream"
        )
    part = document.part.related_parts.get(rid)
    if part is None:
        return DocxMissingImage(reference=rid, media_type="application/octet-stream")
    transform = _transform(element)
    if isinstance(transform, str):
        return DocxMissingImage(
            reference=f"{part.partname} ({transform})", media_type=part.content_type
        )
    raster = _probe(part.blob)
    if raster is None:
        return DocxMissingImage(reference=str(part.partname), media_type=part.content_type)
    if transform.is_noop and not raster.animated and raster.format in _BYTE_EXACT_MEDIA_TYPES:
        return DocxImage(
            payload=part.blob,
            media_type=_BYTE_EXACT_MEDIA_TYPES[raster.format],
            width=raster.width,
            height=raster.height,
        )
    decoded = (
        _transformed_as_png(part.blob, transform)
        if not transform.is_noop
        else _raster_as_png(part.blob)
    )
    if decoded is None:
        return DocxMissingImage(reference=str(part.partname), media_type=part.content_type)
    payload, width, height = decoded
    return DocxImage(payload=payload, media_type="image/png", width=width, height=height)


def _probe(payload: bytes) -> _Raster | None:
    """A payload's actual Pillow format and first-frame size, or None when unreadable."""
    probed = probe_image_payload(payload)
    if probed is None:
        return None
    return _Raster(
        format=probed.format,
        width=probed.width,
        height=probed.height,
        animated=probed.animated,
    )


def _transform(element: BaseOxmlElement | None) -> _Transform | str:
    """The picture's reproducible transform, or a note naming what cannot be reproduced."""
    if element is None:
        return _Transform()
    if element.tag == _V_IMAGEDATA:
        return _vml_transform(element)
    return _drawingml_transform(element)


def _drawingml_transform(blip: BaseOxmlElement) -> _Transform | str:
    """Read the nearest ``pic:pic`` shape: crop, flips and rotation, or a gate note."""
    for child in blip:
        if child.tag != _EXT_LST:
            return _IMAGE_EFFECT
    picture = _nearest_picture(blip)
    if picture is None:
        return _Transform()
    fill = picture.find(_BLIP_FILL)
    properties = picture.find(_SP_PR)
    if fill is None or properties is None:
        return _Transform()
    if fill.find(_TILE) is not None:
        return _TILED_IMAGE
    geometry = _geometry_note(properties)
    if geometry is not None:
        return geometry
    crop = _crop(fill)
    if isinstance(crop, str):
        return crop
    frame = properties.find(_XFRM)
    if frame is None:
        return _Transform(crop=crop)
    flip_h = _flag(frame, "flipH")
    if isinstance(flip_h, str):
        return flip_h
    flip_v = _flag(frame, "flipV")
    if isinstance(flip_v, str):
        return flip_v
    turns = _quarter_turns(frame.get("rot"))
    if isinstance(turns, str):
        return turns
    return _Transform(crop=crop, flip_h=flip_h, flip_v=flip_v, quarter_turns=turns)


def _vml_transform(data: BaseOxmlElement) -> _Transform | str:
    """A VML preview: camera-ready only without a crop, effect, rotation or flip."""
    for name in _VML_CROP_ATTRIBUTES:
        raw = data.get(name)
        if raw is not None and _vml_amount(raw) != 0.0:
            return _VML_CROP
    for name in _VML_EFFECT_ATTRIBUTES:
        raw = data.get(name)
        if raw is not None and _vml_effect(raw):
            return _IMAGE_EFFECT
    for ancestor in data.iterancestors():
        style = ancestor.get("style")
        if style is not None and _style_has_transform(style):
            return _VML_TRANSFORM
    return _Transform()


def _vml_amount(raw: str) -> float:
    """A VML numeric attribute; an unreadable value counts as a real transform."""
    try:
        return float(raw)
    except ValueError:
        return 1.0


def _vml_effect(raw: str) -> bool:
    """A VML boolean effect attribute; ``f``/``false``/``0`` keep the picture clean."""
    return raw.strip().lower() not in ("f", "false", "0", "none")


def _style_has_transform(style: str) -> bool:
    for declaration in style.split(";"):
        name, _, value = declaration.partition(":")
        name = name.strip().lower()
        value = value.strip()
        if name == "flip" and value:
            return True
        if name == "rotation" and _vml_amount(value) != 0.0:
            return True
    return False


def _geometry_note(properties: BaseOxmlElement) -> str | None:
    geometry = properties.find(_PRST_GEOM)
    if geometry is not None and geometry.get("prst") not in (None, "rect"):
        return _SHAPE_GEOMETRY
    if properties.find(_CUST_GEOM) is not None:
        return _CUSTOM_GEOMETRY
    if any(properties.find(tag) is not None for tag in _SHAPE_EFFECTS):
        return _IMAGE_EFFECT
    return None


def _crop(fill: BaseOxmlElement) -> tuple[int, int, int, int] | str | None:
    """The ``a:srcRect`` crop in percent 100000 units, None for a no-op, or a gate note."""
    rect = fill.find(_SRC_RECT)
    if rect is None:
        return None
    values: list[int] = []
    for attribute in ("l", "t", "r", "b"):
        raw = rect.get(attribute)
        if raw is None:
            values.append(0)
            continue
        try:
            value = int(raw)
        except ValueError:
            return _CROP_INVALID
        if not 0 <= value < 100000:
            return _CROP_INVALID
        values.append(value)
    left, top, right, bottom = values
    if left + right >= 100000 or top + bottom >= 100000:
        return _CROP_EMPTY
    return None if not any(values) else (left, top, right, bottom)


def _flag(frame: BaseOxmlElement, name: str) -> bool | str:
    raw = frame.get(name)
    if raw in (None, "0", "false"):
        return False
    if raw in ("1", "true"):
        return True
    return _FLIP_INVALID


def _quarter_turns(raw: str | None) -> int | str:
    """Word's clockwise rotation in quarter turns; anything else is a gate note."""
    if raw is None:
        return 0
    try:
        value = int(raw) % _FULL_TURN
    except ValueError:
        return _ROTATION_INVALID
    if value % _QUARTER_TURN:
        return _ROTATION_NOT_QUARTER
    return value // _QUARTER_TURN


def _nearest_picture(blip: BaseOxmlElement) -> BaseOxmlElement | None:
    for ancestor in blip.iterancestors():
        if isinstance(ancestor, BaseOxmlElement) and ancestor.tag == _PIC:
            return ancestor
    return None


def _transformed_as_png(payload: bytes, transform: _Transform) -> tuple[bytes, int, int] | None:
    """The decoded first frame with crop, flips and clockwise quarter turns, as PNG."""
    try:
        with Image.open(io.BytesIO(payload)) as image:
            frame = _frame(image)
            if transform.crop is not None:
                box = _crop_box(transform.crop, frame.size)
                if box is None:
                    return None
                frame = frame.crop(box)
            if transform.flip_h:
                frame = frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            if transform.flip_v:
                frame = frame.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            # Word turns clockwise; Pillow's quarter-turn transposes turn counterclockwise.
            if transform.quarter_turns == 1:
                frame = frame.transpose(Image.Transpose.ROTATE_270)
            elif transform.quarter_turns == 2:
                frame = frame.transpose(Image.Transpose.ROTATE_180)
            elif transform.quarter_turns == 3:
                frame = frame.transpose(Image.Transpose.ROTATE_90)
            return _png_bytes(frame)
    except (OSError, ValueError, Image.DecompressionBombError):
        return None


def _raster_as_png(payload: bytes) -> tuple[bytes, int, int] | None:
    """The first frame of any readable raster payload, as PNG, or None when undecodable."""
    try:
        with Image.open(io.BytesIO(payload)) as image:
            return _png_bytes(_frame(image))
    except (OSError, ValueError, Image.DecompressionBombError):
        return None


def _frame(image: Image.Image) -> Image.Image:
    """The first frame in a PNG-safe mode; alpha in the mode or metadata is kept."""
    has_alpha_band = any(band.upper() == "A" for band in image.getbands())
    return image.convert("RGBA" if has_alpha_band or "transparency" in image.info else "RGB")


def _png_bytes(image: Image.Image) -> tuple[bytes, int, int]:
    """PNG bytes of exactly these pixels; a fresh canvas drops source metadata and EXIF."""
    width, height = image.size
    clean = Image.new(image.mode, image.size)
    # Copy every band, alpha included; never composite an alpha picture onto opaque black.
    clean.paste(image, (0, 0))
    output = io.BytesIO()
    clean.save(output, format="PNG")
    return output.getvalue(), width, height


def _crop_box(
    crop: tuple[int, int, int, int], size: tuple[int, int]
) -> tuple[int, int, int, int] | None:
    """The pixel box one ``a:srcRect`` selects, or None when it selects no pixels."""
    width, height = size
    left, top, right, bottom = crop
    box = (
        width * left // 100000,
        height * top // 100000,
        width - width * right // 100000,
        height - height * bottom // 100000,
    )
    return None if box[0] >= box[2] or box[1] >= box[3] else box
