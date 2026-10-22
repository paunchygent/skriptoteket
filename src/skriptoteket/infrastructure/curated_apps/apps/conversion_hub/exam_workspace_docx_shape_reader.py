"""Reads one Word drawing made of shapes into the figure model (TASK-SKRIPT-39-04-22, D2, D3).

Purpose:
    ``read_shape_figure`` reads one ``w:drawing`` element (ECMA-376 DrawingML with the Word 2010
    ``wps``, ``wpg`` and ``wpc`` shape containers) into a ``ShapeFigure``. The reader is exact:
    every element and attribute value it does not model raises ``UnsupportedShapeFigure`` that
    names it, so a figure is either complete or not returned at all (D3). ``a:extLst`` is the one
    exception: ECMA-376 makes extension lists ignorable, so the allowlists of the property
    elements that carry one admit and skip it (``exam_workspace_docx_shape_xml`` lists them).

    Coordinates and group transforms (where each shape's box lands in the figure, and how group
    rotation and mirrors compose) live in ``exam_workspace_docx_shape_transforms``.

Relationships:
    - ``exam_workspace_docx_shape_figure`` holds the figure model the reader fills.
    - ``exam_workspace_docx_shape_xml`` holds the namespaces and the exact XML helpers;
      ``exam_workspace_docx_shape_colors`` resolves colours and ``wps:style`` references through
      the theme; ``exam_workspace_docx_shape_labels`` reads the text box labels.
    - ``exam_workspace_docx_shape_transforms`` maps group and canvas coordinates into the
      figure box.
    - ``exam_workspace_docx_chunker`` calls ``read_shape_figure`` for a drawing block without a
      picture; ``exam_workspace_docx_shape_drawing`` draws the figure.
"""

from __future__ import annotations

import re

from docx.document import Document as DocxDocument

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_colors import (  # noqa: E501
    Theme,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_figure import (  # noqa: E501
    Arrowhead,
    ArrowheadKind,
    ArrowheadSize,
    DashStyle,
    FigureShape,
    PresetGeometry,
    ShapeFigure,
    ShapeOutline,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_labels import (  # noqa: E501
    LabelReader,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_transforms import (  # noqa: E501
    ShapeMapping,
    wrap_degrees,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_xml import (  # noqa: E501
    DRAWINGML_NS,
    EXT_LST,
    WORD_CANVAS_NS,
    WORD_CANVAS_URI,
    WORD_DRAWING_NS,
    WORD_GROUP_NS,
    WORD_GROUP_URI,
    WORD_SHAPE_NS,
    WORD_SHAPE_URI,
    Element,
    elements,
    flag,
    int_attr,
    int_attr_or,
    local_name,
    only,
    tag_name,
    unsupported,
)

_DEFAULT_LINE_EMU = 9525
_FILL_CHOICES = frozenset(
    f"{DRAWINGML_NS}{name}"
    for name in ("noFill", "solidFill", "gradFill", "blipFill", "pattFill", "grpFill")
)
_EFFECT_ELEMENTS = frozenset(
    f"{DRAWINGML_NS}{name}" for name in ("effectLst", "effectDag", "scene3d", "sp3d")
)
_SP_PR_CHILDREN = (
    _FILL_CHOICES
    | _EFFECT_ELEMENTS
    | {f"{DRAWINGML_NS}{n}" for n in ("xfrm", "prstGeom", "custGeom", "ln")}
    | {EXT_LST}
)
_LN_CHILDREN = frozenset(
    f"{DRAWINGML_NS}{name}"
    for name in (
        "noFill", "solidFill", "gradFill", "pattFill", "prstDash", "custDash",
        "round", "bevel", "miter", "headEnd", "tailEnd", "extLst",
    )
)  # fmt: skip
_WSP_CHILDREN = frozenset(
    f"{WORD_SHAPE_NS}{name}"
    for name in ("cNvPr", "cNvSpPr", "cNvCnPr", "spPr", "style", "txbx", "bodyPr")
)
_STYLE_CHILDREN = frozenset(
    f"{DRAWINGML_NS}{name}" for name in ("lnRef", "fillRef", "effectRef", "fontRef")
)
_GROUP_NON_VISUAL = frozenset(
    f"{WORD_GROUP_NS}{name}" for name in ("cNvPr", "cNvGrpSpPr", "grpSpPr")
)
_PRESETS: dict[str, PresetGeometry] = {
    "rect": "rect", "roundRect": "roundRect", "ellipse": "ellipse", "triangle": "triangle",
    "rtTriangle": "rtTriangle", "line": "line", "straightConnector1": "straightConnector1",
    "rightArrow": "rightArrow", "leftArrow": "leftArrow", "upArrow": "upArrow",
    "downArrow": "downArrow",
}  # fmt: skip
_ARROWHEAD_KINDS: dict[str, ArrowheadKind] = {
    "triangle": "triangle", "arrow": "arrow", "stealth": "stealth", "oval": "oval",
    "diamond": "diamond",
}  # fmt: skip
_ARROWHEAD_SIZES: dict[str, ArrowheadSize] = {"sm": "sm", "med": "med", "lg": "lg"}
_DASH_STYLES: dict[str, DashStyle] = {
    "solid": "solid", "dash": "dash", "sysDash": "sysDash", "dot": "dot", "sysDot": "sysDot",
    "lgDash": "lgDash", "dashDot": "dashDot", "sysDashDot": "sysDashDot",
}  # fmt: skip
_GUIDE = re.compile(r"val\s+(-?\d+)")


def _is_empty(element: Element) -> bool:
    return len(element) == 0 and not element.attrib


def _arrowhead_size(end: Element, attribute: str, tag: str) -> ArrowheadSize:
    name = end.get(attribute, "med")
    size = _ARROWHEAD_SIZES.get(name)
    if size is None:
        raise unsupported(f"a:{tag}/@{attribute}={name!r}")
    return size


def _check_canvas_layer(layer: Element) -> None:
    """``wpc:bg`` and ``wpc:whole`` may only say "no fill" and "no outline"."""
    for child in elements(layer):
        if child.tag in (f"{DRAWINGML_NS}noFill", EXT_LST):
            continue
        if child.tag == f"{DRAWINGML_NS}ln" and all(
            c.tag in (f"{DRAWINGML_NS}noFill", EXT_LST) for c in elements(child)
        ):
            continue
        raise unsupported(f"{tag_name(layer)} carries {tag_name(child)}")


def _check_visible(non_visual: Element | None) -> None:
    if non_visual is not None and flag(non_visual, "hidden"):
        raise unsupported(f"hidden {tag_name(non_visual)}")


class _FigureReader:
    """One reading of one drawing; the theme is parsed at most once."""

    def __init__(self, document: DocxDocument) -> None:
        self._theme = Theme(document)
        self._labels = LabelReader(document, self._theme)

    def read(self, drawing: Element) -> ShapeFigure:
        containers = elements(drawing)
        if len(containers) != 1 or containers[0].tag not in (
            f"{WORD_DRAWING_NS}inline",
            f"{WORD_DRAWING_NS}anchor",
        ):
            raise unsupported("drawing without exactly one wp:inline or wp:anchor")
        container = containers[0]
        extent = container.find(f"{WORD_DRAWING_NS}extent")
        if extent is None:
            raise unsupported("drawing without wp:extent")
        width, height = int_attr(extent, "cx"), int_attr(extent, "cy")
        # A straight horizontal or vertical line has a zero side; a figure needs one non-zero side.
        if min(width, height) < 0 or max(width, height) == 0:
            raise unsupported(f"wp:extent {width} x {height}")
        data = container.find(f"{DRAWINGML_NS}graphic/{DRAWINGML_NS}graphicData")
        if data is None:
            raise unsupported("drawing without a:graphicData")
        uri = data.get("uri") or ""
        roots = elements(data)
        shapes: list[FigureShape] = []
        if uri == WORD_SHAPE_URI:
            root = self._single(roots, f"{WORD_SHAPE_NS}wsp", "wps:wsp")
            shapes.append(self._shape(root, ShapeMapping(), box=(width, height)))
        elif uri == WORD_GROUP_URI:
            root = self._single(roots, f"{WORD_GROUP_NS}wgp", "wpg:wgp")
            self._walk(root, ShapeMapping().nested(root, box=(width, height)), shapes)
        elif uri == WORD_CANVAS_URI:
            self._walk(
                self._single(roots, f"{WORD_CANVAS_NS}wpc", "wpc:wpc"), ShapeMapping(), shapes
            )
        else:
            raise unsupported(f"graphic data of kind {uri.rsplit('/', 1)[-1]} ({uri})")
        if not shapes:
            raise unsupported("no shapes")
        return ShapeFigure(width_emu=width, height_emu=height, shapes=tuple(shapes))

    @staticmethod
    def _single(roots: list[Element], tag: str, name: str) -> Element:
        if len(roots) != 1 or roots[0].tag != tag:
            raise unsupported(f"graphic data without exactly one {name}")
        return roots[0]

    def _walk(self, parent: Element, mapping: ShapeMapping, shapes: list[FigureShape]) -> None:
        for child in elements(parent):
            if child.tag == f"{WORD_SHAPE_NS}wsp":
                shapes.append(self._shape(child, mapping, box=None))
            elif child.tag == f"{WORD_GROUP_NS}grpSp":
                self._walk(child, mapping.nested(child, box=None), shapes)
            elif child.tag == f"{WORD_GROUP_NS}cNvPr":
                _check_visible(child)
            elif child.tag in _GROUP_NON_VISUAL:
                continue
            elif parent.tag == f"{WORD_CANVAS_NS}wpc" and child.tag in (
                f"{WORD_CANVAS_NS}bg",
                f"{WORD_CANVAS_NS}whole",
            ):
                _check_canvas_layer(child)
            else:
                raise unsupported(f"{tag_name(child)} in {tag_name(parent)}")

    # --- one shape ---

    def _shape(
        self, wsp: Element, mapping: ShapeMapping, *, box: tuple[int, int] | None
    ) -> FigureShape:
        children = only(wsp, _WSP_CHILDREN)
        sp_pr = next((c for c in children if c.tag == f"{WORD_SHAPE_NS}spPr"), None)
        if sp_pr is None:
            raise unsupported("wps:wsp without wps:spPr")
        _check_visible(wsp.find(f"{WORD_SHAPE_NS}cNvPr"))
        style = self._style(wsp.find(f"{WORD_SHAPE_NS}style"))
        properties = only(sp_pr, _SP_PR_CHILDREN)
        xfrm = next((c for c in properties if c.tag == f"{DRAWINGML_NS}xfrm"), None)
        if xfrm is None:
            raise unsupported("wps:spPr without a:xfrm")
        off, ext = xfrm.find(f"{DRAWINGML_NS}off"), xfrm.find(f"{DRAWINGML_NS}ext")
        if off is None or ext is None:
            raise unsupported("a:xfrm without a:off and a:ext")
        width, height = float(int_attr(ext, "cx")), float(int_attr(ext, "cy"))
        centre = (
            (box[0] / 2, box[1] / 2)
            if box is not None
            else (int_attr(off, "x") + width / 2, int_attr(off, "y") + height / 2)
        )
        placed = mapping.place(
            centre=centre,
            size=(width, height),
            rotation=wrap_degrees(int_attr_or(xfrm, "rot", 0) / 60000),
            flip_h=flag(xfrm, "flipH"),
            flip_v=flag(xfrm, "flipV"),
        )
        preset, adjustments = self._geometry(properties)
        self._check_effects(properties, style)
        return FigureShape(
            preset=preset,
            x_emu=placed.x,
            y_emu=placed.y,
            width_emu=placed.width,
            height_emu=placed.height,
            rotation_deg=placed.rotation,
            flip_h=placed.flip_h,
            flip_v=placed.flip_v,
            adjustments=adjustments,
            fill=self._fill(properties, style),
            outline=self._outline(properties, style),
            label=self._labels.read(children, style),
        )

    @staticmethod
    def _geometry(properties: list[Element]) -> tuple[PresetGeometry, tuple[tuple[str, int], ...]]:
        if any(c.tag == f"{DRAWINGML_NS}custGeom" for c in properties):
            raise unsupported("a:custGeom")
        geometry = next((c for c in properties if c.tag == f"{DRAWINGML_NS}prstGeom"), None)
        if geometry is None:
            raise unsupported("shape without a:prstGeom geometry")
        name = geometry.get("prst") or ""
        preset = _PRESETS.get(name)
        if preset is None:
            raise unsupported(f"preset geometry {name!r}")
        guides: list[tuple[str, int]] = []
        for container in only(geometry, frozenset({f"{DRAWINGML_NS}avLst"})):
            for guide in only(container, frozenset({f"{DRAWINGML_NS}gd"})):
                formula = _GUIDE.fullmatch(guide.get("fmla") or "")
                if formula is None:
                    raise unsupported(f"a:gd fmla {guide.get('fmla')!r}")
                guides.append((guide.get("name") or "", int(formula.group(1))))
        return preset, tuple(guides)

    def _style(self, style: Element | None) -> dict[str, Element]:
        """The ``wps:style`` references by local name (``lnRef``, ``fillRef`` and so on)."""
        if style is None:
            return {}
        return {local_name(ref): ref for ref in only(style, _STYLE_CHILDREN)}

    # --- fill, outline, effects ---

    def _fill(self, properties: list[Element], style: dict[str, Element]) -> str | None:
        fills = [c for c in properties if c.tag in _FILL_CHOICES]
        if len(fills) > 1:
            raise unsupported("more than one fill in wps:spPr")
        if fills:
            if fills[0].tag == f"{DRAWINGML_NS}noFill":
                return None
            if fills[0].tag != f"{DRAWINGML_NS}solidFill":
                raise unsupported(f"{tag_name(fills[0])} fill")
            return self._theme.solid(fills[0], None)
        index, color = self._theme.reference(style.get("fillRef"))
        if index == 0:
            return None
        entry = self._theme.style_entry("fillStyleLst", index)
        if entry.tag != f"{DRAWINGML_NS}solidFill":
            raise unsupported(f"theme fill style {index} is {tag_name(entry)}")
        return self._theme.solid(entry, color)

    def _outline(self, properties: list[Element], style: dict[str, Element]) -> ShapeOutline | None:
        line = next((c for c in properties if c.tag == f"{DRAWINGML_NS}ln"), None)
        fill = None
        if line is not None:
            if line.get("cmpd") not in (None, "sng"):
                raise unsupported(f"compound line {line.get('cmpd')!r}")
            fill = next((c for c in only(line, _LN_CHILDREN) if c.tag in _FILL_CHOICES), None)
            if fill is not None and fill.tag == f"{DRAWINGML_NS}noFill":
                return None
            if fill is not None and fill.tag != f"{DRAWINGML_NS}solidFill":
                raise unsupported(f"{tag_name(fill)} outline")
        index, color = self._theme.reference(style.get("lnRef"))
        entry = self._theme.style_entry("lnStyleLst", index) if index else None
        sources = [source for source in (line, entry) if source is not None]
        if entry is not None:
            only(entry, _LN_CHILDREN)
        if fill is None:
            if entry is None:
                return None
            fill = next((c for c in elements(entry) if c.tag in _FILL_CHOICES), None)
            if fill is None or fill.tag != f"{DRAWINGML_NS}solidFill":
                found = "no fill" if fill is None else tag_name(fill)
                raise unsupported(f"theme line style {index} has {found}, not a solid line")
        width = next(
            (int_attr(source, "w") for source in sources if source.get("w") is not None),
            _DEFAULT_LINE_EMU,
        )
        if width < 0:
            raise unsupported(f"negative line width {width}")
        return ShapeOutline(
            color=self._theme.solid(fill, color),
            width_emu=width,
            dash=self._dash(sources),
            head=self._arrowhead(sources, "headEnd"),
            tail=self._arrowhead(sources, "tailEnd"),
        )

    @staticmethod
    def _dash(sources: list[Element]) -> DashStyle:
        for source in sources:
            if source.find(f"{DRAWINGML_NS}custDash") is not None:
                raise unsupported("a:custDash")
            dash = source.find(f"{DRAWINGML_NS}prstDash")
            if dash is not None:
                value = dash.get("val") or ""
                style = _DASH_STYLES.get(value)
                if style is None:
                    raise unsupported(f"a:prstDash {value!r}")
                return style
        return "solid"

    @staticmethod
    def _arrowhead(sources: list[Element], tag: str) -> Arrowhead | None:
        end = next((e for s in sources if (e := s.find(f"{DRAWINGML_NS}{tag}")) is not None), None)
        kind_name = "none" if end is None else end.get("type", "none")
        if end is None or kind_name == "none":
            return None
        kind = _ARROWHEAD_KINDS.get(kind_name)
        if kind is None:
            raise unsupported(f"a:{tag} type {kind_name!r}")
        return Arrowhead(
            kind,
            _arrowhead_size(end, "w", tag),
            _arrowhead_size(end, "len", tag),
        )

    def _check_effects(self, properties: list[Element], style: dict[str, Element]) -> None:
        own_list = False
        for effect in (c for c in properties if c.tag in _EFFECT_ELEMENTS):
            if not _is_empty(effect):
                raise unsupported(f"{tag_name(effect)} with content")
            own_list = own_list or effect.tag in (
                f"{DRAWINGML_NS}effectLst",
                f"{DRAWINGML_NS}effectDag",
            )
        ref = style.get("effectRef")
        index = 0 if ref is None else int_attr(ref, "idx")
        if index and not own_list:
            entry = self._theme.style_entry("effectStyleLst", index)
            for effect in (c for c in elements(entry) if c.tag in _EFFECT_ELEMENTS):
                if not _is_empty(effect):
                    raise unsupported(f"theme effect style {index} holds {tag_name(effect)}")


def read_shape_figure(drawing: Element, document: DocxDocument) -> ShapeFigure:
    """Read one ``w:drawing`` of Word shapes into a ``ShapeFigure``.

    Args:
        drawing: The ``w:drawing`` element; the document's theme and styles resolve its
            style references.
        document: The python-docx document the drawing belongs to.

    Raises:
        UnsupportedShapeFigure: An element, attribute value or container outside D2; the
            exception's ``reason`` names it.
    """
    return _FigureReader(document).read(drawing)


__all__ = ["read_shape_figure"]
