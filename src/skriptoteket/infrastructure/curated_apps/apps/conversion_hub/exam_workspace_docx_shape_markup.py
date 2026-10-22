"""Self-contained markup of a Word drawing, kept for Word export (D8, D9, D12).

Purpose:
    ``self_contained_shapes`` serializes one ``w:drawing`` so the Word export can write it
    into a new document and draw what the picture drew. Two things tie a drawing to its source
    package, and the stored copy carries neither:

    - Another part of the package: a relationship attribute, a footnote, endnote or comment
      reference, an object or a pict (D12). Such a drawing has no stored copy.
    - The source theme and styles: ``a:schemeClr`` colours, ``wps:style`` references and the
      paragraph and character styles of a label. The export document has other themes and
      styles, so the same markup would be drawn in other colours and fonts.

    The second is resolved from the ``ShapeFigure`` the reader built from the same drawing: the
    figure holds each shape's fill, outline and label marks as the picture drew them, so they are
    written onto the matching ``wps:wsp`` as explicit values. A shape's fill and outline become
    ``a:solidFill``/``a:noFill`` and ``a:ln`` with ``a:srgbClr``; ``wps:style`` is removed; every
    label paragraph gets ``w:jc`` and every label run ``w:b``, ``w:i``, ``w:color``, ``w:sz`` and
    ``w:u`` (no ``w:themeColor``), and ``w:pStyle`` and ``w:rStyle`` are removed. ``a:extLst`` is
    removed: the reader reads nothing from it and its ``a14:hiddenFill`` copies only serve a VML
    fallback the export does not write.

Relationships:
    - ``exam_workspace_docx_shape_reader`` builds the figure; the reader emits shapes in document
      order of ``wps:wsp``, which is the order this module pairs them in.
    - ``exam_workspace_docx_chunker`` stores the returned markup on the drawn picture.
    - ``exam_workspace_docx_writer`` writes the stored markup into the export.
"""

import copy

from docx.oxml.ns import qn
from docx.oxml.xmlchemy import BaseOxmlElement
from lxml import etree

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_figure import (  # noqa: E501
    FigureShape,
    LabelAlign,
    LabelParagraph,
    LabelRun,
    ShapeFigure,
    ShapeOutline,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_xml import (  # noqa: E501
    DRAWINGML_NS,
    EXT_LST,
    WORD_SHAPE_NS,
    WORDPROCESSINGML_NS,
)

_RELATIONSHIPS_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
# Elements that point at another part of the document or hold content from one.
_OTHER_PART_TAGS = frozenset(
    qn(tag)
    for tag in (
        "w:footnoteReference",
        "w:endnoteReference",
        "w:commentReference",
        "w:object",
        "w:pict",
    )
)
_A = DRAWINGML_NS
_W = WORDPROCESSINGML_NS
_FILL_TAGS = frozenset(f"{_A}{name}" for name in ("noFill", "solidFill"))
_LINE_OWN_TAGS = _FILL_TAGS | {f"{_A}{name}" for name in ("prstDash", "headEnd", "tailEnd")}
# Child order of the elements this module writes into (ECMA-376 sequences).
_PPR_ORDER = (
    "pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl", "numPr",
    "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap",
    "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd",
    "snapToGrid", "spacing", "ind", "contextualSpacing", "mirrorIndents", "suppressOverlap",
    "jc", "textDirection", "textAlignment", "textboxTightWrap", "outlineLvl", "divId",
    "cnfStyle", "rPr", "sectPr", "pPrChange",
)  # fmt: skip
_RPR_ORDER = (
    "rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike",
    "outline", "shadow", "emboss", "imprint", "noProof", "snapToGrid", "vanish", "webHidden",
    "color", "spacing", "w", "kern", "position", "sz", "szCs", "highlight", "u", "effect",
    "bdr", "shd", "fitText", "vertAlign", "rtl", "cs", "em", "lang", "eastAsianLayout",
    "specVanish", "oMath",
)  # fmt: skip
_JUSTIFICATION: dict[LabelAlign, str] = {
    "left": "left",
    "center": "center",
    "right": "right",
    "justify": "both",
}
# What would still resolve against the source package once the shapes state their own values.
_SOURCE_DEPENDENT_TAGS = frozenset(
    {f"{_A}schemeClr", f"{WORD_SHAPE_NS}style", f"{_W}pStyle", f"{_W}rStyle"}
)
_RUN_TEXT_PARTS = {"t", "tab", "noBreakHyphen", "br", "cr"}


def self_contained_shapes(drawing: BaseOxmlElement, figure: ShapeFigure) -> str | None:
    """The ``w:drawing`` as standalone XML that states its own colours and label marks, or None.

    ``figure`` is what ``read_shape_figure`` read from this very drawing. None means the
    drawing needs another part of the package (a relationship attribute or a footnote,
    endnote, comment, object or pict element) or its shapes do not pair with the figure's, so
    the picture alone is kept. Otherwise every namespace the subtree uses is declared on the
    serialized root; the source tree stays untouched and ids are kept.
    """
    for element in drawing.iter():
        if element.tag in _OTHER_PART_TAGS:
            return None
        if any(
            isinstance(name, str) and name.startswith(_RELATIONSHIPS_NS) for name in element.attrib
        ):
            return None
    stored: etree._Element = copy.deepcopy(drawing)
    for extension_list in list(stored.iter(EXT_LST)):
        extension_list.getparent().remove(extension_list)
    wsps = list(stored.iter(f"{WORD_SHAPE_NS}wsp"))
    if len(wsps) != len(figure.shapes):
        return None
    for wsp, shape in zip(wsps, figure.shapes, strict=True):
        if not _state_shape(wsp, shape):
            return None
    if any(element.tag in _SOURCE_DEPENDENT_TAGS for element in stored.iter(etree.Element)):
        return None
    markup: str = etree.tostring(stored, encoding="unicode")
    return markup


# --- one shape ---------------------------------------------------------------------------------


def _state_shape(wsp: etree._Element, shape: FigureShape) -> bool:
    """Write the shape's resolved fill, outline and label onto ``wsp``; False if they do not fit."""
    for style in wsp.findall(f"{WORD_SHAPE_NS}style"):
        wsp.remove(style)
    properties = wsp.find(f"{WORD_SHAPE_NS}spPr")
    geometry = None if properties is None else properties.find(f"{_A}prstGeom")
    if properties is None or geometry is None:
        return False
    for fill in [c for c in properties if c.tag in _FILL_TAGS]:
        properties.remove(fill)
    fill = _fill(properties, shape.fill)
    geometry.addnext(fill)
    line = properties.find(f"{_A}ln")
    if line is None:
        line = etree.Element(f"{_A}ln")
        fill.addnext(line)
    _state_outline(line, shape.outline)
    text_box = wsp.find(f"{WORD_SHAPE_NS}txbx")
    if text_box is None:
        return True
    paragraphs = text_box.findall(f"{_W}txbxContent/{_W}p")
    for style in [*text_box.iter(f"{_W}pStyle"), *text_box.iter(f"{_W}rStyle")]:
        style.getparent().remove(style)
    if shape.label is None:
        return True
    marks = shape.label.paragraphs
    if len(paragraphs) != len(marks):
        return False
    return all(_state_paragraph(p, mark) for p, mark in zip(paragraphs, marks, strict=True))


def _fill(parent: etree._Element, color: str | None) -> etree._Element:
    if color is None:
        return parent.makeelement(f"{_A}noFill")
    solid = parent.makeelement(f"{_A}solidFill")
    etree.SubElement(solid, f"{_A}srgbClr").set("val", color)
    return solid


def _state_outline(line: etree._Element, outline: ShapeOutline | None) -> None:
    """Make ``line`` the outline the picture drew; the join and cap children stay."""
    if outline is None:
        line.attrib.clear()
        for child in list(line):
            line.remove(child)
        line.append(line.makeelement(f"{_A}noFill"))
        return
    for child in [c for c in line if c.tag in _LINE_OWN_TAGS]:
        line.remove(child)
    line.set("w", str(outline.width_emu))
    line.insert(0, _fill(line, outline.color))
    if outline.dash != "solid":
        dash = line.makeelement(f"{_A}prstDash")
        dash.set("val", outline.dash)
        line.insert(1, dash)
    for tag, end in (("headEnd", outline.head), ("tailEnd", outline.tail)):
        if end is not None:
            element = line.makeelement(f"{_A}{tag}")
            element.set("type", end.kind)
            element.set("w", end.width)
            element.set("len", end.length)
            line.append(element)


# --- one label ---------------------------------------------------------------------------------


def _state_paragraph(p: etree._Element, mark: LabelParagraph) -> bool:
    properties = p.find(f"{_W}pPr")
    if properties is None:
        properties = p.makeelement(f"{_W}pPr")
        p.insert(0, properties)
    _put(properties, _word_element(properties, "jc", _JUSTIFICATION[mark.align]), _PPR_ORDER)
    runs = [r for r in p.findall(f"{_W}r") if _run_text(r)]
    if len(runs) != len(mark.runs):
        return False
    if any(_run_text(r) != m.text for r, m in zip(runs, mark.runs, strict=True)):
        return False
    for r, run_mark in zip(runs, mark.runs, strict=True):
        _state_run(r, run_mark)
    return True


def _run_text(r: etree._Element) -> str:
    """The text of a label run as ``LabelReader`` reads it (tab as a space, break as newline)."""
    text = ""
    for part in r:
        name = etree.QName(part).localname if isinstance(part.tag, str) else ""
        if name not in _RUN_TEXT_PARTS:
            continue
        if name == "t":
            text += part.text or ""
        elif name == "tab":
            text += " "
        elif name == "noBreakHyphen":
            text += "-"
        else:
            text += "\n"
    return text


def _state_run(r: etree._Element, mark: LabelRun) -> None:
    properties = r.find(f"{_W}rPr")
    if properties is None:
        properties = r.makeelement(f"{_W}rPr")
        r.insert(0, properties)
    underline = properties.find(f"{_W}u")
    kept_underline = (
        underline is not None and underline.get(f"{_W}val", "single") != "none" and mark.underline
    )
    for name in ("b", "i", "color", "sz", "u"):
        for old in properties.findall(f"{_W}{name}"):
            if not (name == "u" and kept_underline):
                properties.remove(old)
    _put(properties, _word_element(properties, "b", None if mark.bold else "0"), _RPR_ORDER)
    _put(properties, _word_element(properties, "i", None if mark.italic else "0"), _RPR_ORDER)
    _put(properties, _word_element(properties, "color", mark.color), _RPR_ORDER)
    _put(properties, _word_element(properties, "sz", str(round(mark.size_pt * 2))), _RPR_ORDER)
    if mark.underline and not kept_underline:
        _put(properties, _word_element(properties, "u", "single"), _RPR_ORDER)


def _word_element(parent: etree._Element, name: str, value: str | None) -> etree._Element:
    element = parent.makeelement(f"{_W}{name}")
    if value is not None:
        element.set(f"{_W}val", value)
    return element


def _put(parent: etree._Element, element: etree._Element, order: tuple[str, ...]) -> None:
    """Insert ``element`` in ``parent`` in schema order, replacing a child of the same name."""
    name = etree.QName(element).localname
    for old in parent.findall(element.tag):
        parent.remove(old)
    rank = order.index(name)
    position = len(parent)
    for index, child in enumerate(parent):
        child_name = etree.QName(child).localname if isinstance(child.tag, str) else ""
        if child_name in order and order.index(child_name) > rank:
            position = index
            break
    parent.insert(position, element)
