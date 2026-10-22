"""Colours and theme for Word shape drawings (TASK-SKRIPT-39-04-22, D2, D3).

Purpose:
    Resolves DrawingML colours, through the document's theme part where a colour or a
    ``wps:style`` reference points into it. Any colour form it does not model raises
    ``UnsupportedShapeFigure`` naming it.

    Colours. ``a:srgbClr``, ``a:sysClr/@lastClr``, ``a:schemeClr`` (through the theme part) and
    ``a:prstClr`` black or white, with the modifiers ``lumMod``, ``lumOff`` (HSL lightness
    multiplied or offset by value / 100000), ``shade`` and ``tint`` and ``alpha`` of 100000.
    ECMA-376 defines ``shade`` as "x% of the colour combined with (100 - x)% black" and ``tint`` as
    "x% of the colour combined with (100 - x)% white" without naming the colour space; the reader
    mixes in linear-light sRGB, which is what Word draws (accent1 4472C4 with shade 50000 is
    2F528F in Word).

Relationships:
    - ``exam_workspace_docx_shape_xml`` holds the namespaces and exact XML helpers used here.
    - ``exam_workspace_docx_shape_reader`` resolves fills and outlines with ``Theme``.
    - ``exam_workspace_docx_shape_labels`` resolves the label font colour with ``Theme``.
"""

from __future__ import annotations

import colorsys
import re
from typing import cast

from docx.document import Document as DocxDocument
from docx.opc.constants import RELATIONSHIP_TYPE
from lxml import etree  # type: ignore[import-untyped]  # transitive of python-docx, no stubs

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_xml import (  # noqa: E501
    DRAWINGML_NS,
    Element,
    elements,
    int_attr,
    tag_name,
    unsupported,
)

Rgb = tuple[float, float, float]

HEX = re.compile(r"[0-9A-Fa-f]{6}")

_COLOR_ELEMENTS = frozenset(
    f"{DRAWINGML_NS}{name}" for name in ("srgbClr", "sysClr", "schemeClr", "prstClr")
)
_THEME_SLOTS = frozenset(
    {"dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5",
     "accent6", "hlink", "folHlink"}
)  # fmt: skip
_SCHEME_ALIASES = {"bg1": "lt1", "tx1": "dk1", "bg2": "lt2", "tx2": "dk2"}


def _to_linear(channel: float) -> float:
    value = channel / 255
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def _from_linear(linear: float) -> float:
    value = 12.92 * linear if linear <= 0.0031308 else 1.055 * linear ** (1 / 2.4) - 0.055
    return value * 255


def _literal_color(element: Element) -> Rgb | None:
    """Return the colour of ``srgbClr``, ``sysClr`` or ``prstClr``; None for any other element."""
    if element.tag == f"{DRAWINGML_NS}srgbClr":
        value = element.get("val") or ""
    elif element.tag == f"{DRAWINGML_NS}sysClr":
        value = element.get("lastClr") or ""
    elif element.tag == f"{DRAWINGML_NS}prstClr":
        preset = element.get("val")
        if preset not in ("black", "white"):
            raise unsupported(f"preset colour {preset!r}")
        return (0.0, 0.0, 0.0) if preset == "black" else (255.0, 255.0, 255.0)
    else:
        return None
    if not HEX.fullmatch(value):
        raise unsupported(f"{tag_name(element)} colour value {value!r}")
    return float(int(value[0:2], 16)), float(int(value[2:4], 16)), float(int(value[4:6], 16))


def _modified(rgb: Rgb, element: Element) -> Rgb:
    """Apply the colour element's modifiers in document order."""
    for modifier in elements(element):
        amount = int_attr(modifier, "val") / 100000
        local = etree.QName(modifier).localname
        if modifier.tag == f"{DRAWINGML_NS}alpha" and amount == 1:
            continue
        if modifier.tag == f"{DRAWINGML_NS}lumMod" or modifier.tag == f"{DRAWINGML_NS}lumOff":
            hue, light, saturation = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
            light = light * amount if local == "lumMod" else light + amount
            red, green, blue = colorsys.hls_to_rgb(hue, min(1.0, max(0.0, light)), saturation)
            rgb = (red * 255, green * 255, blue * 255)
        elif modifier.tag == f"{DRAWINGML_NS}shade":
            rgb = cast(Rgb, tuple(_from_linear(_to_linear(c) * amount) for c in rgb))
        elif modifier.tag == f"{DRAWINGML_NS}tint":
            rgb = cast(Rgb, tuple(_from_linear(_to_linear(c) * amount + 1 - amount) for c in rgb))
        else:
            raise unsupported(f"colour modifier {tag_name(modifier)} {modifier.get('val')}")
    return rgb


def hex_color(rgb: Rgb) -> str:
    """Upper-case ``RRGGBB`` of a colour, each channel rounded and clamped to 0-255."""
    return "".join(f"{min(255, max(0, round(channel))):02X}" for channel in rgb)


class Theme:
    """The document's theme part, parsed on first use, and the colours that resolve through it."""

    def __init__(self, document: DocxDocument) -> None:
        self._document = document
        self._root: Element | None = None

    @property
    def root(self) -> Element:
        if self._root is None:
            try:
                blob = self._document.part.part_related_by(RELATIONSHIP_TYPE.THEME).blob
            except KeyError:
                raise unsupported("a theme reference without a theme part") from None
            parser = etree.XMLParser(resolve_entities=False, no_network=True)
            try:
                self._root = cast(Element, etree.fromstring(blob, parser))
            except etree.XMLSyntaxError:
                raise unsupported("the theme part is not readable XML") from None
            if self._root.tag != f"{DRAWINGML_NS}theme":
                raise unsupported("the theme part is not an a:theme")
        return self._root

    def scheme_color(self, slot: str) -> Rgb:
        scheme = self.root.find(
            f"{DRAWINGML_NS}themeElements/{DRAWINGML_NS}clrScheme/{DRAWINGML_NS}{slot}"
        )
        children = [] if scheme is None else elements(scheme)
        color = _literal_color(children[0]) if len(children) == 1 else None
        if color is None:
            raise unsupported(f"theme colour {slot} is not a plain colour")
        return color

    def style_entry(self, list_name: str, index: int) -> Element:
        """Return the 1-based entry of a theme ``fmtScheme`` style list (fill, ln or effect)."""
        styles = self.root.find(
            f"{DRAWINGML_NS}themeElements/{DRAWINGML_NS}fmtScheme/{DRAWINGML_NS}{list_name}"
        )
        entries = [] if styles is None else elements(styles)
        if not 1 <= index <= len(entries):
            raise unsupported(f"theme {list_name} has no entry {index}")
        return entries[index - 1]

    def color(self, element: Element, placeholder: Rgb | None) -> Rgb:
        """Resolve a colour element; ``phClr`` takes ``placeholder``, the style reference colour."""
        rgb = _literal_color(element)
        if rgb is None:
            if element.tag != f"{DRAWINGML_NS}schemeClr":
                raise unsupported(f"colour {tag_name(element)}")
            value = element.get("val") or ""
            if value == "phClr":
                if placeholder is None:
                    raise unsupported("phClr without a style reference colour")
                rgb = placeholder
            elif (slot := _SCHEME_ALIASES.get(value, value)) in _THEME_SLOTS:
                rgb = self.scheme_color(slot)
            else:
                raise unsupported(f"scheme colour {value!r}")
        return _modified(rgb, element)

    def reference_color(self, ref: Element | None) -> Rgb | None:
        """Return the colour of a ``wps:style`` reference, or None when it has none."""
        colors = [] if ref is None else [c for c in elements(ref) if c.tag in _COLOR_ELEMENTS]
        return self.color(colors[0], None) if colors else None

    def reference(self, ref: Element | None) -> tuple[int, Rgb | None]:
        """Return the ``idx`` and the colour of an ``lnRef`` or ``fillRef`` (0 when absent)."""
        if ref is None:
            return 0, None
        return int_attr(ref, "idx"), self.reference_color(ref)

    def solid(self, solid: Element, placeholder: Rgb | None) -> str:
        """The hex colour of an ``a:solidFill``; ``phClr`` in it takes ``placeholder``."""
        colors = elements(solid)
        if len(colors) != 1 or colors[0].tag not in _COLOR_ELEMENTS:
            raise unsupported(f"{tag_name(solid)} without exactly one colour")
        return hex_color(self.color(colors[0], placeholder))


__all__ = ["HEX", "Rgb", "Theme", "hex_color"]
