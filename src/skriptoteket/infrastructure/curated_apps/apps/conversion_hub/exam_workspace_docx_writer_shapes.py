"""A picture's stored Word shapes, written as an editable inline drawing (TASK-SKRIPT-39-04-22 D9).

Purpose:
    ``write_stored_shapes`` writes the ``w:drawing`` markup an asset stores into a paragraph of
    the Word export, in place of the picture drawn from it. The stored copy is prepared first:

    - It must parse, be one ``w:drawing`` around an inline or anchored shape graphic (group,
      single shape or canvas), have a readable size and reference no relationship (D12);
      otherwise nothing is written and the caller writes the picture.
    - An anchor becomes a ``wp:inline`` with no wrap distance, keeping only its content.
    - A drawing wider than the text column is scaled to fit: the extent and the root shape box
      keep their aspect, a group keeps its child coordinate space, and a canvas, which cannot
      scale its contents, keeps its source size.
    - Identity attributes Word regenerates (``w14:paraId``, ``w14:textId``, ``wp14:anchorId``,
      ``wp14:editId`` and every ``w:rsid*``) are removed.
    - The copy gets fresh drawing ids, allocated as python-docx allocates a picture's (the
      document part's next free id); each connector follows its shapes' new ids.

    The drawing sits in a run the way Word writes a shape: ``mc:AlternateContent/mc:Choice``
    requiring the shape namespace, with no ``mc:Fallback``.

Relationships:
    - ``exam_workspace_docx_shape_markup`` produces the stored markup at import.
    - ``exam_workspace_docx_writer`` renders the student copy and calls ``write_stored_shapes``
      for each picture whose asset stores shapes.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import NamedTuple

from docx.shared import Length
from docx.text.paragraph import Paragraph
from lxml import etree

_NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_NS_WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
_NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NS_MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
_NS_W14 = "http://schemas.microsoft.com/office/word/2010/wordml"
_NS_WP14 = "http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing"
_NS_WPG = "http://schemas.microsoft.com/office/word/2010/wordprocessingGroup"
_NS_WPS = "http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
_NS_WPC = "http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas"
# The shape kinds Word 2010+ writes inside ``mc:Choice``: graphicData uri -> required prefix.
_SHAPE_GRAPHIC_PREFIXES: Mapping[str, str] = MappingProxyType(
    {_NS_WPG: "wpg", _NS_WPS: "wps", _NS_WPC: "wpc"}
)
# The root shape's own size box inside each scalable shape graphic, found from graphicData.
_ROOT_SIZE_PATHS: Mapping[str, str] = MappingProxyType(
    {
        f"{{{_NS_WPG}}}wgp": f"{{{_NS_WPG}}}grpSpPr/{{{_NS_A}}}xfrm/{{{_NS_A}}}ext",
        f"{{{_NS_WPS}}}wsp": f"{{{_NS_WPS}}}spPr/{{{_NS_A}}}xfrm/{{{_NS_A}}}ext",
    }
)
# Identity attributes Word regenerates; a stored copy would repeat them for every export.
_DROPPED_SHAPE_ATTRIBUTES = frozenset(
    {
        f"{{{_NS_W14}}}paraId",
        f"{{{_NS_W14}}}textId",
        f"{{{_NS_WP14}}}anchorId",
        f"{{{_NS_WP14}}}editId",
    }
)
_INLINE_CHILDREN = ("extent", "effectExtent", "docPr", "cNvGraphicFramePr", "graphic")
_SHAPE_ID_ELEMENTS = frozenset({"docPr", "cNvPr"})
_CONNECTION_ELEMENTS = frozenset({"stCxn", "endCxn"})
_SHAPE_PARSER = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False)


def write_stored_shapes(paragraph: Paragraph, stored: str, limit: Length) -> bool:
    """Write a picture's stored Word shapes in the paragraph; False leaves it untouched.

    The copy gets fresh drawing ids, allocated as python-docx allocates a picture's
    (the document part's next free id), and sits in a run the way Word writes
    a shape: ``mc:AlternateContent/mc:Choice`` requiring the shape namespace.
    """
    prepared = _prepared_shapes(stored, limit)
    if prepared is None:
        return False
    _renumbered(prepared.drawing, paragraph.part.next_id)
    run = paragraph.add_run()
    alternate = etree.SubElement(run._r, f"{{{_NS_MC}}}AlternateContent", nsmap={"mc": _NS_MC})
    choice = etree.SubElement(
        alternate,
        f"{{{_NS_MC}}}Choice",
        {"Requires": prepared.prefix},
        nsmap={prepared.prefix: prepared.namespace},
    )
    choice.append(prepared.drawing)
    return True


class _PreparedShapes(NamedTuple):
    """A stored drawing ready to insert: the namespace its ``mc:Choice`` must require."""

    drawing: etree._Element
    prefix: str
    namespace: str


def _renumbered(drawing: etree._Element, first_id: int) -> None:
    """Give the drawing fresh ids from ``first_id`` and keep its connectors on their shapes.

    Each ``a:stCxn``/``a:endCxn`` follows its shape's old-to-new id in this one drawing;
    a connection naming a shape the drawing does not hold is removed.
    """
    next_id = first_id
    new_by_old_shape_id: dict[str, str] = {}
    for element in drawing.iter(etree.Element):
        if etree.QName(element).localname not in _SHAPE_ID_ELEMENTS:
            continue
        if etree.QName(element).localname == "cNvPr":
            new_by_old_shape_id.setdefault(element.get("id", ""), str(next_id))
        element.set("id", str(next_id))
        next_id += 1
    connections = [
        element
        for element in drawing.iter(etree.Element)
        if etree.QName(element).localname in _CONNECTION_ELEMENTS
    ]
    for connection in connections:
        new_id = new_by_old_shape_id.get(connection.get("id", ""))
        if new_id is not None:
            connection.set("id", new_id)
            continue
        parent = connection.getparent()
        if parent is not None:
            parent.remove(connection)


def _prepared_shapes(stored: str, limit: Length) -> _PreparedShapes | None:
    """Parse stored ``w:drawing`` markup and turn it into an inline drawing, or None.

    None means the markup is unusable and the picture is written instead: it does not
    parse, is not one ``w:drawing`` around an inline or anchored shape graphic, has no
    readable size, or references a relationship (D12). A drawing wider than the text
    column is scaled to fit instead.
    """
    try:
        drawing = etree.fromstring(stored, parser=_SHAPE_PARSER)
    except (etree.XMLSyntaxError, ValueError):
        return None
    if drawing.tag != f"{{{_NS_W}}}drawing" or len(drawing) != 1:
        return None
    if any(
        etree.QName(name).namespace == _NS_R
        for element in drawing.iter(etree.Element)
        for name in element.attrib
    ):
        return None
    frame = drawing[0]
    if frame.tag not in (f"{{{_NS_WP}}}inline", f"{{{_NS_WP}}}anchor"):
        return None
    graphic_data = frame.find(f"{{{_NS_A}}}graphic/{{{_NS_A}}}graphicData")
    extent = frame.find(f"{{{_NS_WP}}}extent")
    if graphic_data is None or extent is None or frame.find(f"{{{_NS_WP}}}docPr") is None:
        return None
    namespace = graphic_data.get("uri", "")
    prefix = _SHAPE_GRAPHIC_PREFIXES.get(namespace)
    width = extent.get("cx", "")
    height = extent.get("cy", "")
    if prefix is None or not width.isdigit() or not height.isdigit():
        return None
    if int(width) > limit and not _fitted_to_width(graphic_data, extent, limit):
        return None
    inline = _as_inline(frame)
    drawing.replace(frame, inline)
    for element in drawing.iter(etree.Element):
        for name in list(element.attrib):
            if name in _DROPPED_SHAPE_ATTRIBUTES or (
                etree.QName(name).namespace == _NS_W
                and etree.QName(name).localname.startswith("rsid")
            ):
                del element.attrib[name]
    return _PreparedShapes(drawing, prefix, namespace)


def _fitted_to_width(graphic_data: etree._Element, extent: etree._Element, limit: Length) -> bool:
    """Scale the drawing's extent and root shape box to the text width, keeping its aspect.

    A group keeps its child coordinate space, so it scales its children; a canvas cannot
    scale its contents and keeps the source size. False means the root box is unreadable.
    """
    if len(graphic_data) != 1:
        return False
    root = graphic_data[0]
    if root.tag == f"{{{_NS_WPC}}}wpc":
        return True
    box_path = _ROOT_SIZE_PATHS.get(root.tag)
    box = root.find(box_path) if box_path is not None else None
    if box is None:
        return False
    scale = int(limit) / int(extent.get("cx", ""))
    for element in (extent, box):
        sides = [element.get("cx", ""), element.get("cy", "")]
        if not all(side.isdigit() for side in sides):
            return False
        for name, side in zip(("cx", "cy"), sides, strict=True):
            element.set(name, str(round(int(side) * scale)))
    extent.set("cx", str(int(limit)))
    return True


def _as_inline(frame: etree._Element) -> etree._Element:
    """The frame as a ``wp:inline`` with no wrap distance; an anchor keeps only its content."""
    inline = etree.Element(
        f"{{{_NS_WP}}}inline",
        {name: "0" for name in ("distT", "distB", "distL", "distR")},
    )
    kept = [
        child
        for child in frame
        if isinstance(child.tag, str) and etree.QName(child).localname in _INLINE_CHILDREN
    ]
    for child in sorted(
        kept, key=lambda element: _INLINE_CHILDREN.index(etree.QName(element).localname)
    ):
        inline.append(child)
    return inline
