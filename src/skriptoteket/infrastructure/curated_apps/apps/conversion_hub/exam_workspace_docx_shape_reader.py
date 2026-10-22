"""Reads one Word drawing made of shapes into the figure model (TASK-SKRIPT-39-04-22, D2, D3).

Purpose:
    ``read_shape_figure`` reads one ``w:drawing`` element (ECMA-376 DrawingML with the Word 2010
    ``wps``, ``wpg`` and ``wpc`` shape containers) into a ``ShapeFigure``. The reader is exact:
    every element and attribute value it does not model raises ``UnsupportedShapeFigure`` that
    names it, so a figure is either complete or not returned at all (D3).

    Coordinates. The figure box is ``wp:extent``. A single shape fills the box. A group maps its
    child space onto the parent as ``x_parent = off.x + (x - chOff.x) * ext.cx / chExt.cx`` (the
    same for y); nested groups compose their mappings and the top-level group maps onto the
    figure box. A canvas child is already in EMU of the box.

    Colours. ``a:srgbClr``, ``a:sysClr/@lastClr``, ``a:schemeClr`` (through the theme part) and
    ``a:prstClr`` black or white, with the modifiers ``lumMod``, ``lumOff`` (HSL lightness
    multiplied or offset by value / 100000), ``shade`` and ``tint`` and ``alpha`` of 100000.
    ECMA-376 defines ``shade`` as "x% of the colour combined with (100 - x)% black" and ``tint`` as
    "x% of the colour combined with (100 - x)% white" without naming the colour space; the reader
    mixes in linear-light sRGB, which is what Word draws (accent1 4472C4 with shade 50000 is
    2F528F in Word).

Relationships:
    - ``exam_workspace_docx_shape_figure`` holds the figure model the reader fills.
    - ``exam_workspace_docx_chunker`` calls ``read_shape_figure`` for a drawing block without a
      picture; ``exam_workspace_docx_shape_drawing`` draws the figure.
"""

from __future__ import annotations

import colorsys
import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import cast, get_args

from docx.document import Document as DocxDocument
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml.xmlchemy import BaseOxmlElement
from docx.styles.style import CharacterStyle
from docx.text.paragraph import Paragraph
from docx.text.run import Run
from lxml import etree  # type: ignore[import-untyped]  # transitive of python-docx, no stubs

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_figure import (  # noqa: E501
    SUPPORTED_PRESETS,
    Arrowhead,
    ArrowheadKind,
    ArrowheadSize,
    DashStyle,
    FigureShape,
    LabelAlign,
    LabelAnchor,
    LabelParagraph,
    LabelRun,
    PresetGeometry,
    ShapeFigure,
    ShapeLabel,
    ShapeOutline,
    UnsupportedShapeFigure,
)

_Element = BaseOxmlElement
_Rgb = tuple[float, float, float]

_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
_WPS_NS = "http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
_WPG_NS = "http://schemas.microsoft.com/office/word/2010/wordprocessingGroup"
_WPC_NS = "http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas"
_WPS, _WPG, _WPC = f"{{{_WPS_NS}}}", f"{{{_WPG_NS}}}", f"{{{_WPC_NS}}}"
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_PREFIXES = {
    _A[1:-1]: "a",
    _WP[1:-1]: "wp",
    _W[1:-1]: "w",
    _WPS_NS: "wps",
    _WPG_NS: "wpg",
    _WPC_NS: "wpc",
    "http://schemas.openxmlformats.org/drawingml/2006/picture": "pic",
}

_DEFAULT_LINE_EMU = 9525
_DEFAULT_SIZE_PT = 10.0
_DEFAULT_INSETS = (91440, 45720, 91440, 45720)
_FILL_CHOICES = frozenset(
    f"{_A}{name}" for name in ("noFill", "solidFill", "gradFill", "blipFill", "pattFill", "grpFill")
)
_EFFECT_ELEMENTS = frozenset(
    f"{_A}{name}" for name in ("effectLst", "effectDag", "scene3d", "sp3d")
)
_SP_PR_CHILDREN = (
    _FILL_CHOICES | _EFFECT_ELEMENTS | {f"{_A}{n}" for n in ("xfrm", "prstGeom", "custGeom", "ln")}
)
_LN_CHILDREN = frozenset(
    f"{_A}{name}"
    for name in (
        "noFill", "solidFill", "gradFill", "pattFill", "prstDash", "custDash",
        "round", "bevel", "miter", "headEnd", "tailEnd",
    )
)  # fmt: skip
_WSP_CHILDREN = frozenset(
    f"{_WPS}{name}" for name in ("cNvPr", "cNvSpPr", "cNvCnPr", "spPr", "style", "txbx", "bodyPr")
)
_STYLE_CHILDREN = frozenset(f"{_A}{name}" for name in ("lnRef", "fillRef", "effectRef", "fontRef"))
_GROUP_NON_VISUAL = frozenset(f"{_WPG}{name}" for name in ("cNvPr", "cNvGrpSpPr", "grpSpPr"))
_COLOR_ELEMENTS = frozenset(f"{_A}{name}" for name in ("srgbClr", "sysClr", "schemeClr", "prstClr"))
_THEME_SLOTS = frozenset(
    {"dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5",
     "accent6", "hlink", "folHlink"}
)  # fmt: skip
_SCHEME_ALIASES = {"bg1": "lt1", "tx1": "dk1", "bg2": "lt2", "tx2": "dk2"}
_ARROWHEAD_KINDS = frozenset(get_args(ArrowheadKind))
_ARROWHEAD_SIZES = frozenset(get_args(ArrowheadSize))
_DASH_STYLES = frozenset(get_args(DashStyle))
_ALIGNMENTS: dict[str, LabelAlign] = {
    "left": "left", "start": "left", "center": "center", "right": "right", "end": "right",
    "both": "justify",
}  # fmt: skip
_ANCHORS = frozenset(get_args(LabelAnchor))
_PARAGRAPH_CHILDREN = frozenset(
    f"{_W}{name}" for name in ("pPr", "r", "bookmarkStart", "bookmarkEnd", "proofErr")
)
_RUN_CHILDREN = frozenset(
    f"{_W}{name}"
    for name in ("rPr", "t", "tab", "br", "cr", "noBreakHyphen", "lastRenderedPageBreak")
)
# Direct or inherited run marks that change what Word draws and that the label model lacks.
_UNMODELLED_MARKS = ("strike", "dstrike", "highlight", "shd", "vertAlign", "caps", "smallCaps")
_MARK_OFF = frozenset({"0", "false", "off", "none", "baseline"})
_GUIDE = re.compile(r"val\s+(-?\d+)")
_HEX = re.compile(r"[0-9A-Fa-f]{6}")


def _unsupported(reason: str) -> UnsupportedShapeFigure:
    return UnsupportedShapeFigure(reason)


def _name(element: _Element) -> str:
    qualified = etree.QName(element)
    prefix = _PREFIXES.get(qualified.namespace or "")
    return f"{prefix}:{qualified.localname}" if prefix else qualified.localname


def _elements(parent: _Element) -> list[_Element]:
    """Child elements, without comments and processing instructions."""
    return [child for child in parent if isinstance(child.tag, str)]


def _only(parent: _Element, allowed: frozenset[str]) -> list[_Element]:
    """Return the child elements; any child outside ``allowed`` is unsupported."""
    children = _elements(parent)
    for child in children:
        if child.tag not in allowed:
            raise _unsupported(f"{_name(child)} in {_name(parent)}")
    return children


def _int(element: _Element, attribute: str) -> int:
    value = element.get(attribute)
    try:
        return int(value or "")
    except ValueError:
        raise _unsupported(f"{_name(element)}/@{attribute}={value!r}") from None


def _flag(element: _Element, attribute: str) -> bool:
    value = element.get(attribute)
    if value is None or value in ("0", "false"):
        return False
    if value in ("1", "true"):
        return True
    raise _unsupported(f"{_name(element)}/@{attribute}={value!r}")


def _is_empty(element: _Element) -> bool:
    return len(element) == 0 and not element.attrib


def _chain(style: CharacterStyle | None) -> Iterator[CharacterStyle]:
    """Yield a style and its bases; Word ignores a basedOn cycle, so stop at a repeat."""
    seen: set[str | None] = set()
    while style is not None and style.style_id not in seen:
        seen.add(style.style_id)
        yield style
        style = style.base_style


# --- colours ----------------------------------------------------------------------------------


def _to_linear(channel: float) -> float:
    value = channel / 255
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def _from_linear(linear: float) -> float:
    value = 12.92 * linear if linear <= 0.0031308 else 1.055 * linear ** (1 / 2.4) - 0.055
    return value * 255


def _literal_color(element: _Element) -> _Rgb | None:
    """Return the colour of ``srgbClr``, ``sysClr`` or ``prstClr``; None for any other element."""
    if element.tag == f"{_A}srgbClr":
        value = element.get("val") or ""
    elif element.tag == f"{_A}sysClr":
        value = element.get("lastClr") or ""
    elif element.tag == f"{_A}prstClr":
        preset = element.get("val")
        if preset not in ("black", "white"):
            raise _unsupported(f"preset colour {preset!r}")
        return (0.0, 0.0, 0.0) if preset == "black" else (255.0, 255.0, 255.0)
    else:
        return None
    if not _HEX.fullmatch(value):
        raise _unsupported(f"{_name(element)} colour value {value!r}")
    return float(int(value[0:2], 16)), float(int(value[2:4], 16)), float(int(value[4:6], 16))


def _modified(rgb: _Rgb, element: _Element) -> _Rgb:
    """Apply the colour element's modifiers in document order."""
    for modifier in _elements(element):
        amount = _int(modifier, "val") / 100000
        local = etree.QName(modifier).localname
        if modifier.tag == f"{_A}alpha" and amount == 1:
            continue
        if modifier.tag == f"{_A}lumMod" or modifier.tag == f"{_A}lumOff":
            hue, light, saturation = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
            light = light * amount if local == "lumMod" else light + amount
            red, green, blue = colorsys.hls_to_rgb(hue, min(1.0, max(0.0, light)), saturation)
            rgb = (red * 255, green * 255, blue * 255)
        elif modifier.tag == f"{_A}shade":
            rgb = cast(_Rgb, tuple(_from_linear(_to_linear(c) * amount) for c in rgb))
        elif modifier.tag == f"{_A}tint":
            rgb = cast(_Rgb, tuple(_from_linear(_to_linear(c) * amount + 1 - amount) for c in rgb))
        else:
            raise _unsupported(f"colour modifier {_name(modifier)} {modifier.get('val')}")
    return rgb


def _hex(rgb: _Rgb) -> str:
    return "".join(f"{min(255, max(0, round(channel))):02X}" for channel in rgb)


class _Theme:
    """The document's theme part, parsed on first use."""

    def __init__(self, document: DocxDocument) -> None:
        self._document = document
        self._root: _Element | None = None

    @property
    def root(self) -> _Element:
        if self._root is None:
            try:
                blob = self._document.part.part_related_by(RELATIONSHIP_TYPE.THEME).blob
            except KeyError:
                raise _unsupported("a theme reference without a theme part") from None
            parser = etree.XMLParser(resolve_entities=False, no_network=True)
            try:
                self._root = cast(_Element, etree.fromstring(blob, parser))
            except etree.XMLSyntaxError:
                raise _unsupported("the theme part is not readable XML") from None
            if self._root.tag != f"{_A}theme":
                raise _unsupported("the theme part is not an a:theme")
        return self._root

    def scheme_color(self, slot: str) -> _Rgb:
        scheme = self.root.find(f"{_A}themeElements/{_A}clrScheme/{_A}{slot}")
        children = [] if scheme is None else _elements(scheme)
        color = _literal_color(children[0]) if len(children) == 1 else None
        if color is None:
            raise _unsupported(f"theme colour {slot} is not a plain colour")
        return color

    def style_entry(self, list_name: str, index: int) -> _Element:
        """Return the 1-based entry of a theme ``fmtScheme`` style list (fill, ln or effect)."""
        styles = self.root.find(f"{_A}themeElements/{_A}fmtScheme/{_A}{list_name}")
        entries = [] if styles is None else _elements(styles)
        if not 1 <= index <= len(entries):
            raise _unsupported(f"theme {list_name} has no entry {index}")
        return entries[index - 1]

    def color(self, element: _Element, placeholder: _Rgb | None) -> _Rgb:
        """Resolve a colour element; ``phClr`` takes ``placeholder``, the style reference colour."""
        rgb = _literal_color(element)
        if rgb is None:
            if element.tag != f"{_A}schemeClr":
                raise _unsupported(f"colour {_name(element)}")
            value = element.get("val") or ""
            if value == "phClr":
                if placeholder is None:
                    raise _unsupported("phClr without a style reference colour")
                rgb = placeholder
            elif (slot := _SCHEME_ALIASES.get(value, value)) in _THEME_SLOTS:
                rgb = self.scheme_color(slot)
            else:
                raise _unsupported(f"scheme colour {value!r}")
        return _modified(rgb, element)


# --- geometry ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Mapping:
    """Child coordinates to figure coordinates: ``figure = scale * child + offset``."""

    scale_x: float = 1.0
    scale_y: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0

    def nested(self, group: _Element, *, box: tuple[int, int] | None) -> _Mapping:
        """Return the mapping of a group's children, composed inside this mapping.

        ``box`` replaces the group's own ``off`` and ``ext`` for the top-level group, which
        fills the figure box.
        """
        properties = group.find(f"{_WPG}grpSpPr")
        xfrm = None if properties is None else _only(properties, frozenset({f"{_A}xfrm"}))
        if not xfrm:
            raise _unsupported("group without a:xfrm")
        transform = xfrm[0]
        if (
            _int_or(transform, "rot", 0) != 0
            or _flag(transform, "flipH")
            or _flag(transform, "flipV")
        ):
            raise _unsupported("rotated or flipped group")
        off, ext, ch_off, ch_ext = (
            transform.find(f"{_A}{name}") for name in ("off", "ext", "chOff", "chExt")
        )
        if off is None or ext is None or ch_off is None or ch_ext is None:
            raise _unsupported("group a:xfrm without off, ext, chOff and chExt")
        child_width, child_height = _int(ch_ext, "cx"), _int(ch_ext, "cy")
        if child_width <= 0 or child_height <= 0:
            raise _unsupported("group with an empty a:chExt")
        off_x, off_y = (0, 0) if box else (_int(off, "x"), _int(off, "y"))
        width, height = box or (_int(ext, "cx"), _int(ext, "cy"))
        factor_x, factor_y = width / child_width, height / child_height
        return _Mapping(
            self.scale_x * factor_x,
            self.scale_y * factor_y,
            self.scale_x * (off_x - _int(ch_off, "x") * factor_x) + self.offset_x,
            self.scale_y * (off_y - _int(ch_off, "y") * factor_y) + self.offset_y,
        )

    @property
    def uniform(self) -> bool:
        return abs(self.scale_x - self.scale_y) <= 1e-9 * max(self.scale_x, self.scale_y)


def _int_or(element: _Element, attribute: str, default: int) -> int:
    return default if element.get(attribute) is None else _int(element, attribute)


def _check_canvas_layer(layer: _Element) -> None:
    """``wpc:bg`` and ``wpc:whole`` may only say "no fill" and "no outline"."""
    for child in _elements(layer):
        if child.tag == f"{_A}noFill":
            continue
        if child.tag == f"{_A}ln" and all(c.tag == f"{_A}noFill" for c in _elements(child)):
            continue
        raise _unsupported(f"{_name(layer)} carries {_name(child)}")


def _check_visible(non_visual: _Element | None) -> None:
    if non_visual is not None and _flag(non_visual, "hidden"):
        raise _unsupported(f"hidden {_name(non_visual)}")


class _FigureReader:
    """One reading of one drawing; the theme is parsed at most once."""

    def __init__(self, document: DocxDocument) -> None:
        self._document = document
        self._theme = _Theme(document)

    def read(self, drawing: _Element) -> ShapeFigure:
        containers = _elements(drawing)
        if len(containers) != 1 or containers[0].tag not in (f"{_WP}inline", f"{_WP}anchor"):
            raise _unsupported("drawing without exactly one wp:inline or wp:anchor")
        container = containers[0]
        extent = container.find(f"{_WP}extent")
        if extent is None:
            raise _unsupported("drawing without wp:extent")
        width, height = _int(extent, "cx"), _int(extent, "cy")
        # A straight horizontal or vertical line has a zero side; a figure needs one non-zero side.
        if min(width, height) < 0 or max(width, height) == 0:
            raise _unsupported(f"wp:extent {width} x {height}")
        data = container.find(f"{_A}graphic/{_A}graphicData")
        if data is None:
            raise _unsupported("drawing without a:graphicData")
        uri = data.get("uri") or ""
        roots = _elements(data)
        shapes: list[FigureShape] = []
        if uri == _WPS_NS:
            root = self._single(roots, f"{_WPS}wsp", "wps:wsp")
            shapes.append(self._shape(root, _Mapping(), box=(width, height)))
        elif uri == _WPG_NS:
            root = self._single(roots, f"{_WPG}wgp", "wpg:wgp")
            self._walk(root, _Mapping().nested(root, box=(width, height)), shapes)
        elif uri == _WPC_NS:
            self._walk(self._single(roots, f"{_WPC}wpc", "wpc:wpc"), _Mapping(), shapes)
        else:
            raise _unsupported(f"graphic data of kind {uri.rsplit('/', 1)[-1]} ({uri})")
        if not shapes:
            raise _unsupported("no shapes")
        return ShapeFigure(width_emu=width, height_emu=height, shapes=tuple(shapes))

    @staticmethod
    def _single(roots: list[_Element], tag: str, name: str) -> _Element:
        if len(roots) != 1 or roots[0].tag != tag:
            raise _unsupported(f"graphic data without exactly one {name}")
        return roots[0]

    def _walk(self, parent: _Element, mapping: _Mapping, shapes: list[FigureShape]) -> None:
        for child in _elements(parent):
            if child.tag == f"{_WPS}wsp":
                shapes.append(self._shape(child, mapping, box=None))
            elif child.tag == f"{_WPG}grpSp":
                self._walk(child, mapping.nested(child, box=None), shapes)
            elif child.tag == f"{_WPG}cNvPr":
                _check_visible(child)
            elif child.tag in _GROUP_NON_VISUAL:
                continue
            elif parent.tag == f"{_WPC}wpc" and child.tag in (f"{_WPC}bg", f"{_WPC}whole"):
                _check_canvas_layer(child)
            else:
                raise _unsupported(f"{_name(child)} in {_name(parent)}")

    # --- one shape ---

    def _shape(
        self, wsp: _Element, mapping: _Mapping, *, box: tuple[int, int] | None
    ) -> FigureShape:
        children = _only(wsp, _WSP_CHILDREN)
        sp_pr = next((c for c in children if c.tag == f"{_WPS}spPr"), None)
        if sp_pr is None:
            raise _unsupported("wps:wsp without wps:spPr")
        _check_visible(wsp.find(f"{_WPS}cNvPr"))
        style = self._style(wsp.find(f"{_WPS}style"))
        properties = _only(sp_pr, _SP_PR_CHILDREN)
        xfrm = next((c for c in properties if c.tag == f"{_A}xfrm"), None)
        if xfrm is None:
            raise _unsupported("wps:spPr without a:xfrm")
        off, ext = xfrm.find(f"{_A}off"), xfrm.find(f"{_A}ext")
        if off is None or ext is None:
            raise _unsupported("a:xfrm without a:off and a:ext")
        rotation = (_int_or(xfrm, "rot", 0) / 60000) % 360
        if box is not None:
            x, y, width, height = 0.0, 0.0, float(box[0]), float(box[1])
        else:
            if rotation % 180 and not mapping.uniform:
                raise _unsupported("rotated shape in a group scaled unevenly in x and y")
            x = mapping.scale_x * _int(off, "x") + mapping.offset_x
            y = mapping.scale_y * _int(off, "y") + mapping.offset_y
            width, height = mapping.scale_x * _int(ext, "cx"), mapping.scale_y * _int(ext, "cy")
        preset, adjustments = self._geometry(properties)
        self._check_effects(properties, style)
        return FigureShape(
            preset=preset,
            x_emu=x,
            y_emu=y,
            width_emu=width,
            height_emu=height,
            rotation_deg=rotation,
            flip_h=_flag(xfrm, "flipH"),
            flip_v=_flag(xfrm, "flipV"),
            adjustments=adjustments,
            fill=self._fill(properties, style),
            outline=self._outline(properties, style),
            label=self._label(children, style),
        )

    @staticmethod
    def _geometry(properties: list[_Element]) -> tuple[PresetGeometry, tuple[tuple[str, int], ...]]:
        if any(c.tag == f"{_A}custGeom" for c in properties):
            raise _unsupported("a:custGeom")
        geometry = next((c for c in properties if c.tag == f"{_A}prstGeom"), None)
        if geometry is None:
            raise _unsupported("shape without a:prstGeom geometry")
        name = geometry.get("prst") or ""
        if name not in SUPPORTED_PRESETS:
            raise _unsupported(f"preset geometry {name!r}")
        guides: list[tuple[str, int]] = []
        for container in _only(geometry, frozenset({f"{_A}avLst"})):
            for guide in _only(container, frozenset({f"{_A}gd"})):
                formula = _GUIDE.fullmatch(guide.get("fmla") or "")
                if formula is None:
                    raise _unsupported(f"a:gd fmla {guide.get('fmla')!r}")
                guides.append((guide.get("name") or "", int(formula.group(1))))
        return cast(PresetGeometry, name), tuple(guides)

    def _style(self, style: _Element | None) -> dict[str, _Element]:
        """The ``wps:style`` references by local name (``lnRef``, ``fillRef`` and so on)."""
        if style is None:
            return {}
        return {etree.QName(ref).localname: ref for ref in _only(style, _STYLE_CHILDREN)}

    def _reference_color(self, ref: _Element | None) -> _Rgb | None:
        """Return the colour of a style reference, or None when it has none."""
        colors = [] if ref is None else [c for c in _elements(ref) if c.tag in _COLOR_ELEMENTS]
        return self._theme.color(colors[0], None) if colors else None

    def _reference(self, ref: _Element | None) -> tuple[int, _Rgb | None]:
        """Return the ``idx`` and the colour of an ``lnRef`` or ``fillRef`` (0 when absent)."""
        if ref is None:
            return 0, None
        return _int(ref, "idx"), self._reference_color(ref)

    def _solid(self, solid: _Element, placeholder: _Rgb | None) -> str:
        colors = _elements(solid)
        if len(colors) != 1 or colors[0].tag not in _COLOR_ELEMENTS:
            raise _unsupported(f"{_name(solid)} without exactly one colour")
        return _hex(self._theme.color(colors[0], placeholder))

    # --- fill, outline, effects ---

    def _fill(self, properties: list[_Element], style: dict[str, _Element]) -> str | None:
        fills = [c for c in properties if c.tag in _FILL_CHOICES]
        if len(fills) > 1:
            raise _unsupported("more than one fill in wps:spPr")
        if fills:
            if fills[0].tag == f"{_A}noFill":
                return None
            if fills[0].tag != f"{_A}solidFill":
                raise _unsupported(f"{_name(fills[0])} fill")
            return self._solid(fills[0], None)
        index, color = self._reference(style.get("fillRef"))
        if index == 0:
            return None
        entry = self._theme.style_entry("fillStyleLst", index)
        if entry.tag != f"{_A}solidFill":
            raise _unsupported(f"theme fill style {index} is {_name(entry)}")
        return self._solid(entry, color)

    def _outline(
        self, properties: list[_Element], style: dict[str, _Element]
    ) -> ShapeOutline | None:
        line = next((c for c in properties if c.tag == f"{_A}ln"), None)
        fill = None
        if line is not None:
            if line.get("cmpd") not in (None, "sng"):
                raise _unsupported(f"compound line {line.get('cmpd')!r}")
            fill = next((c for c in _only(line, _LN_CHILDREN) if c.tag in _FILL_CHOICES), None)
            if fill is not None and fill.tag == f"{_A}noFill":
                return None
            if fill is not None and fill.tag != f"{_A}solidFill":
                raise _unsupported(f"{_name(fill)} outline")
        index, color = self._reference(style.get("lnRef"))
        entry = self._theme.style_entry("lnStyleLst", index) if index else None
        sources = [source for source in (line, entry) if source is not None]
        if entry is not None:
            _only(entry, _LN_CHILDREN)
        if fill is None:
            if entry is None:
                return None
            fill = next((c for c in _elements(entry) if c.tag in _FILL_CHOICES), None)
            if fill is None or fill.tag != f"{_A}solidFill":
                found = "no fill" if fill is None else _name(fill)
                raise _unsupported(f"theme line style {index} has {found}, not a solid line")
        width = next(
            (_int(source, "w") for source in sources if source.get("w") is not None),
            _DEFAULT_LINE_EMU,
        )
        if width < 0:
            raise _unsupported(f"negative line width {width}")
        return ShapeOutline(
            color=self._solid(fill, color),
            width_emu=width,
            dash=self._dash(sources),
            head=self._arrowhead(sources, "headEnd"),
            tail=self._arrowhead(sources, "tailEnd"),
        )

    @staticmethod
    def _dash(sources: list[_Element]) -> DashStyle:
        for source in sources:
            if source.find(f"{_A}custDash") is not None:
                raise _unsupported("a:custDash")
            dash = source.find(f"{_A}prstDash")
            if dash is not None:
                value = dash.get("val") or ""
                if value not in _DASH_STYLES:
                    raise _unsupported(f"a:prstDash {value!r}")
                return cast(DashStyle, value)
        return "solid"

    @staticmethod
    def _arrowhead(sources: list[_Element], tag: str) -> Arrowhead | None:
        end = next((e for s in sources if (e := s.find(f"{_A}{tag}")) is not None), None)
        kind = "none" if end is None else end.get("type", "none")
        if end is None or kind == "none":
            return None
        if kind not in _ARROWHEAD_KINDS:
            raise _unsupported(f"a:{tag} type {kind!r}")
        sizes = []
        for attribute in ("w", "len"):
            size = end.get(attribute, "med")
            if size not in _ARROWHEAD_SIZES:
                raise _unsupported(f"a:{tag}/@{attribute}={size!r}")
            sizes.append(cast(ArrowheadSize, size))
        return Arrowhead(cast(ArrowheadKind, kind), sizes[0], sizes[1])

    def _check_effects(self, properties: list[_Element], style: dict[str, _Element]) -> None:
        own_list = False
        for effect in (c for c in properties if c.tag in _EFFECT_ELEMENTS):
            if not _is_empty(effect):
                raise _unsupported(f"{_name(effect)} with content")
            own_list = own_list or effect.tag in (f"{_A}effectLst", f"{_A}effectDag")
        ref = style.get("effectRef")
        index = 0 if ref is None else _int(ref, "idx")
        if index and not own_list:
            entry = self._theme.style_entry("effectStyleLst", index)
            for effect in (c for c in _elements(entry) if c.tag in _EFFECT_ELEMENTS):
                if not _is_empty(effect):
                    raise _unsupported(f"theme effect style {index} holds {_name(effect)}")

    # --- label ---

    def _label(self, children: list[_Element], style: dict[str, _Element]) -> ShapeLabel | None:
        text_box = next((c for c in children if c.tag == f"{_WPS}txbx"), None)
        if text_box is None:
            return None
        content = _only(text_box, frozenset({f"{_W}txbxContent"}))
        if not content:
            return None
        paragraphs = [self._paragraph(p, style) for p in _only(content[0], frozenset({f"{_W}p"}))]
        body = next((c for c in children if c.tag == f"{_WPS}bodyPr"), None)
        insets, anchor = self._body(body)
        if not any(run.text for paragraph in paragraphs for run in paragraph.runs):
            return None
        return ShapeLabel(tuple(paragraphs), *insets, anchor=anchor)

    @staticmethod
    def _body(body: _Element | None) -> tuple[tuple[int, int, int, int], LabelAnchor]:
        if body is None:
            return _DEFAULT_INSETS, "t"
        anchor = body.get("anchor", "t")
        if anchor not in _ANCHORS:
            raise _unsupported(f"wps:bodyPr anchor {anchor!r}")
        if body.get("vert", "horz") != "horz" or _int_or(body, "rot", 0) != 0:
            raise _unsupported("wps:bodyPr with vertical or rotated text")
        if _int_or(body, "numCol", 1) != 1 or _flag(body, "upright") or _flag(body, "anchorCtr"):
            raise _unsupported("wps:bodyPr with columns, upright or centred text")
        for fit in _elements(body):
            if fit.tag in (f"{_A}noAutofit", f"{_A}spAutoFit"):
                continue
            if fit.tag == f"{_A}normAutofit" and not fit.attrib:
                continue
            # Word writes "no text warp" into every text box it saves.
            if fit.tag == f"{_A}prstTxWarp" and fit.get("prst") == "textNoShape":
                continue
            raise _unsupported(f"{_name(fit)} in wps:bodyPr")
        insets = tuple(
            _int_or(body, name, default)
            for name, default in zip(("lIns", "tIns", "rIns", "bIns"), _DEFAULT_INSETS, strict=True)
        )
        return cast(tuple[int, int, int, int], insets), cast(LabelAnchor, anchor)

    def _paragraph(self, p: _Element, style: dict[str, _Element]) -> LabelParagraph:
        children = _only(p, _PARAGRAPH_CHILDREN)
        paragraph = Paragraph(p, self._document)
        properties = p.find(f"{_W}pPr")
        numbering = None if properties is None else properties.find(f"{_W}numPr")
        if numbering is not None:
            number = numbering.find(f"{_W}numId")
            if number is None or number.get(f"{_W}val") != "0":
                raise _unsupported("w:numPr in a label paragraph")
        runs = [self._run(r, paragraph, style) for r in children if r.tag == f"{_W}r"]
        return LabelParagraph(tuple(run for run in runs if run.text), self._alignment(p, paragraph))

    @staticmethod
    def _alignment(p: _Element, paragraph: Paragraph) -> LabelAlign:
        sources = [p, *(s.element for s in _chain(paragraph.style))]
        for source in sources:
            properties = source.find(f"{_W}pPr")
            justification = None if properties is None else properties.find(f"{_W}jc")
            if justification is not None:
                value = justification.get(f"{_W}val") or ""
                if value not in _ALIGNMENTS:
                    raise _unsupported(f"w:jc {value!r}")
                return _ALIGNMENTS[value]
        return "left"

    def _run(self, r: _Element, paragraph: Paragraph, style: dict[str, _Element]) -> LabelRun:
        parts = _only(r, _RUN_CHILDREN)
        marks = self._marks(r, paragraph)
        text = ""
        for part in parts:
            if part.tag == f"{_W}t":
                text += part.text or ""
            elif part.tag == f"{_W}tab":
                text += " "
            elif part.tag == f"{_W}noBreakHyphen":
                text += "-"
            elif part.tag in (f"{_W}br", f"{_W}cr"):
                if part.get(f"{_W}type", "textWrapping") != "textWrapping":
                    raise _unsupported(f"w:br type {part.get(f'{_W}type')!r}")
                text += "\n"
        for mark in (*_UNMODELLED_MARKS, "vanish"):
            active = self._first(marks, mark)
            if text and active is not None and active.get(f"{_W}val") not in _MARK_OFF:
                raise _unsupported(f"w:{mark} on a label run")
        underline = self._first(marks, "u")
        return LabelRun(
            text=text,
            size_pt=self._size(marks),
            color=self._text_color(marks, style),
            bold=self._toggle(marks, "b"),
            italic=self._toggle(marks, "i"),
            underline=underline is not None and underline.get(f"{_W}val", "single") != "none",
        )

    def _marks(self, r: _Element, paragraph: Paragraph) -> list[_Element]:
        """The ``w:rPr`` that apply to a run, strongest first: run, its styles, paragraph styles."""
        run = Run(r, paragraph)
        sources = [
            r,
            *(s.element for s in _chain(run.style)),
            *(s.element for s in _chain(paragraph.style)),
        ]  # noqa: E501
        return [rpr for source in sources if (rpr := source.find(f"{_W}rPr")) is not None]

    @staticmethod
    def _first(marks: list[_Element], tag: str) -> _Element | None:
        return next((m for rpr in marks if (m := rpr.find(f"{_W}{tag}")) is not None), None)

    def _toggle(self, marks: list[_Element], tag: str) -> bool:
        mark = self._first(marks, tag)
        if mark is None:
            return False
        value = mark.get(f"{_W}val", "1")
        if value in ("1", "true", "on"):
            return True
        if value in ("0", "false", "off"):
            return False
        raise _unsupported(f"w:{tag} w:val={value!r}")

    def _size(self, marks: list[_Element]) -> float:
        size = self._first(marks, "sz")
        if size is None:
            styles = self._document.styles.element
            size = styles.find(f"{_W}docDefaults/{_W}rPrDefault/{_W}rPr/{_W}sz")
        return _DEFAULT_SIZE_PT if size is None else _int_w(size) / 2

    def _text_color(self, marks: list[_Element], style: dict[str, _Element]) -> str:
        color = self._first(marks, "color")
        if color is not None:
            value = color.get(f"{_W}val") or ""
            # With a w:themeColor Word still stores the resolved colour in w:val.
            if value == "auto" and color.get(f"{_W}themeColor") is not None:
                raise _unsupported("w:color/@w:themeColor without a resolved w:val")
            if value != "auto":
                if not _HEX.fullmatch(value):
                    raise _unsupported(f"w:color {value!r}")
                return value.upper()
        font_color = self._reference_color(style.get("fontRef"))
        return "000000" if font_color is None else _hex(font_color)


def _int_w(element: _Element) -> int:
    value = element.get(f"{_W}val")
    try:
        return int(value or "")
    except ValueError:
        raise _unsupported(f"{_name(element)} w:val={value!r}") from None


def read_shape_figure(drawing: BaseOxmlElement, document: DocxDocument) -> ShapeFigure:
    """Read one ``w:drawing`` of Word shapes into a ``ShapeFigure``.

    Args:
        drawing: The ``w:drawing`` element; the document's theme and styles resolve its
            style references.
        document: The python-docx document the drawing belongs to.

    Raises:
        UnsupportedShapeFigure: Any element, attribute value or container outside D2; the
            exception's ``reason`` names it.
    """
    return _FigureReader(document).read(drawing)


__all__ = ["read_shape_figure"]
