"""Colours, theme and exact XML reading for Word shape drawings (TASK-SKRIPT-39-04-22, D2, D3).

Purpose:
    The lowest layer of the shape reader. It holds the exact XML helpers every shape module uses
    (each raises ``UnsupportedShapeFigure`` naming what it does not model) and resolves DrawingML
    colours, through the document's theme part where a colour or a ``wps:style`` reference
    points into it.

    Colours. ``a:srgbClr``, ``a:sysClr/@lastClr``, ``a:schemeClr`` (through the theme part) and
    ``a:prstClr`` black or white, with the modifiers ``lumMod``, ``lumOff`` (HSL lightness
    multiplied or offset by value / 100000), ``shade`` and ``tint`` and ``alpha`` of 100000.
    ECMA-376 defines ``shade`` as "x% of the colour combined with (100 - x)% black" and ``tint`` as
    "x% of the colour combined with (100 - x)% white" without naming the colour space; the reader
    mixes in linear-light sRGB, which is what Word draws (accent1 4472C4 with shade 50000 is
    2F528F in Word).

    Extension lists. ``a:extLst`` is ignorable by ECMA-376; Word writes ``a14:hiddenFill`` and
    ``a14:hiddenLine`` there for the VML fallback, which nothing draws. The allowlists of
    ``a:spPr``, ``a:ln`` (shape and theme line styles), ``wpg:grpSpPr``, ``wps:bodyPr`` and the
    canvas layers admit ``EXT_LST`` and read nothing from it.

Relationships:
    - ``exam_workspace_docx_shape_reader`` reads shapes, fills and outlines with these helpers.
    - ``exam_workspace_docx_shape_labels`` reads text box labels and their font colour.
"""

from __future__ import annotations

import colorsys
import re
from typing import cast

from docx.document import Document as DocxDocument
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml.xmlchemy import BaseOxmlElement
from lxml import etree  # type: ignore[import-untyped]  # transitive of python-docx, no stubs

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_figure import (  # noqa: E501
    UnsupportedShapeFigure,
)

Element = BaseOxmlElement
Rgb = tuple[float, float, float]

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
WPS_NS = "http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
WPG_NS = "http://schemas.microsoft.com/office/word/2010/wordprocessingGroup"
WPC_NS = "http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas"
WPS, WPG, WPC = f"{{{WPS_NS}}}", f"{{{WPG_NS}}}", f"{{{WPC_NS}}}"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
EXT_LST = f"{A}extLst"
FILL_CHOICES = frozenset(
    f"{A}{name}" for name in ("noFill", "solidFill", "gradFill", "blipFill", "pattFill", "grpFill")
)
HEX = re.compile(r"[0-9A-Fa-f]{6}")

_PREFIXES = {
    A[1:-1]: "a",
    WP[1:-1]: "wp",
    W[1:-1]: "w",
    WPS_NS: "wps",
    WPG_NS: "wpg",
    WPC_NS: "wpc",
    "http://schemas.openxmlformats.org/drawingml/2006/picture": "pic",
}
_COLOR_ELEMENTS = frozenset(f"{A}{name}" for name in ("srgbClr", "sysClr", "schemeClr", "prstClr"))
_THEME_SLOTS = frozenset(
    {"dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5",
     "accent6", "hlink", "folHlink"}
)  # fmt: skip
_SCHEME_ALIASES = {"bg1": "lt1", "tx1": "dk1", "bg2": "lt2", "tx2": "dk2"}


# --- exact XML reading -------------------------------------------------------------------------


def unsupported(reason: str) -> UnsupportedShapeFigure:
    return UnsupportedShapeFigure(reason)


def tag_name(element: Element) -> str:
    """The element's prefixed name as Word writes it, for the unsupported reason."""
    qualified = etree.QName(element)
    prefix = _PREFIXES.get(qualified.namespace or "")
    return f"{prefix}:{qualified.localname}" if prefix else qualified.localname


def elements(parent: Element) -> list[Element]:
    """Child elements, without comments and processing instructions."""
    return [child for child in parent if isinstance(child.tag, str)]


def only(parent: Element, allowed: frozenset[str]) -> list[Element]:
    """Return the child elements; any child outside ``allowed`` is unsupported."""
    children = elements(parent)
    for child in children:
        if child.tag not in allowed:
            raise unsupported(f"{tag_name(child)} in {tag_name(parent)}")
    return children


def int_attr(element: Element, attribute: str) -> int:
    value = element.get(attribute)
    try:
        return int(value or "")
    except ValueError:
        raise unsupported(f"{tag_name(element)}/@{attribute}={value!r}") from None


def int_attr_or(element: Element, attribute: str, default: int) -> int:
    return default if element.get(attribute) is None else int_attr(element, attribute)


def flag(element: Element, attribute: str) -> bool:
    value = element.get(attribute)
    if value is None or value in ("0", "false"):
        return False
    if value in ("1", "true"):
        return True
    raise unsupported(f"{tag_name(element)}/@{attribute}={value!r}")


# --- colours ----------------------------------------------------------------------------------


def _to_linear(channel: float) -> float:
    value = channel / 255
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def _from_linear(linear: float) -> float:
    value = 12.92 * linear if linear <= 0.0031308 else 1.055 * linear ** (1 / 2.4) - 0.055
    return value * 255


def _literal_color(element: Element) -> Rgb | None:
    """Return the colour of ``srgbClr``, ``sysClr`` or ``prstClr``; None for any other element."""
    if element.tag == f"{A}srgbClr":
        value = element.get("val") or ""
    elif element.tag == f"{A}sysClr":
        value = element.get("lastClr") or ""
    elif element.tag == f"{A}prstClr":
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
        if modifier.tag == f"{A}alpha" and amount == 1:
            continue
        if modifier.tag == f"{A}lumMod" or modifier.tag == f"{A}lumOff":
            hue, light, saturation = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
            light = light * amount if local == "lumMod" else light + amount
            red, green, blue = colorsys.hls_to_rgb(hue, min(1.0, max(0.0, light)), saturation)
            rgb = (red * 255, green * 255, blue * 255)
        elif modifier.tag == f"{A}shade":
            rgb = cast(Rgb, tuple(_from_linear(_to_linear(c) * amount) for c in rgb))
        elif modifier.tag == f"{A}tint":
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
            if self._root.tag != f"{A}theme":
                raise unsupported("the theme part is not an a:theme")
        return self._root

    def scheme_color(self, slot: str) -> Rgb:
        scheme = self.root.find(f"{A}themeElements/{A}clrScheme/{A}{slot}")
        children = [] if scheme is None else elements(scheme)
        color = _literal_color(children[0]) if len(children) == 1 else None
        if color is None:
            raise unsupported(f"theme colour {slot} is not a plain colour")
        return color

    def style_entry(self, list_name: str, index: int) -> Element:
        """Return the 1-based entry of a theme ``fmtScheme`` style list (fill, ln or effect)."""
        styles = self.root.find(f"{A}themeElements/{A}fmtScheme/{A}{list_name}")
        entries = [] if styles is None else elements(styles)
        if not 1 <= index <= len(entries):
            raise unsupported(f"theme {list_name} has no entry {index}")
        return entries[index - 1]

    def color(self, element: Element, placeholder: Rgb | None) -> Rgb:
        """Resolve a colour element; ``phClr`` takes ``placeholder``, the style reference colour."""
        rgb = _literal_color(element)
        if rgb is None:
            if element.tag != f"{A}schemeClr":
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


__all__ = [
    "A",
    "EXT_LST",
    "FILL_CHOICES",
    "HEX",
    "W",
    "WP",
    "WPC",
    "WPC_NS",
    "WPG",
    "WPG_NS",
    "WPS",
    "WPS_NS",
    "Element",
    "Rgb",
    "Theme",
    "elements",
    "flag",
    "hex_color",
    "int_attr",
    "int_attr_or",
    "only",
    "tag_name",
    "unsupported",
]
