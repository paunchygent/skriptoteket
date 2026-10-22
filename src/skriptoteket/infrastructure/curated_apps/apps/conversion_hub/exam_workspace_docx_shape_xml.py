"""Exact XML reading for Word shape drawings (TASK-SKRIPT-39-04-22, D2, D3).

Purpose:
    The lowest layer of the shape reader. It holds the namespaces and the exact XML helpers every
    shape module uses; each helper raises ``UnsupportedShapeFigure`` naming what it does not
    model.

    Namespaces. A ``*_URI`` constant is the bare namespace URI, as ``a:graphicData/@uri`` states
    it. A ``*_NS`` constant is the same namespace in lxml's Clark form ``{uri}``, so
    ``f"{DRAWINGML_NS}xfrm"`` is the tag ``a:xfrm``. ``docx.oxml.ns.qn`` is not used here because
    python-docx registers no ``wps``, ``wpg`` or ``wpc`` prefix.

    Extension lists. ``a:extLst`` is ignorable by ECMA-376; Word writes ``a14:hiddenFill`` and
    ``a14:hiddenLine`` there for the VML fallback, which nothing draws. The allowlists of
    ``a:spPr``, ``a:ln`` (shape and theme line styles), ``wpg:grpSpPr``, ``wps:bodyPr`` and the
    canvas layers admit ``EXT_LST`` and read nothing from it.

Relationships:
    - ``exam_workspace_docx_shape_reader`` reads shapes, fills and outlines with these helpers.
    - ``exam_workspace_docx_shape_colors`` resolves colours and theme references with them.
    - ``exam_workspace_docx_shape_labels`` reads text box labels with them.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Protocol, overload

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_figure import (  # noqa: E501
    UnsupportedShapeFigure,
)


class Element(Protocol):
    """The lxml element API the shape modules read with.

    lxml ships no type information. Elements that python-docx has no class for, such as every
    ``wps``, ``wpg`` and ``wpc`` element and the parsed theme part, are plain lxml elements, not
    ``BaseOxmlElement``; the protocol names exactly what a plain lxml element and python-docx's
    classes share. ``tag`` is the Clark name ``{uri}local``; comments and processing instructions
    carry a function there, which ``elements`` filters out.
    """

    @property
    def tag(self) -> str: ...

    @property
    def attrib(self) -> Mapping[str, str]: ...

    @property
    def text(self) -> str | None: ...

    @overload
    def get(self, key: str) -> str | None: ...

    @overload
    def get(self, key: str, default: str) -> str: ...

    def find(self, path: str) -> Element | None: ...

    def __iter__(self) -> Iterator[Element]: ...

    def __len__(self) -> int: ...


DRAWINGML_URI = "http://schemas.openxmlformats.org/drawingml/2006/main"
WORD_DRAWING_URI = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
WORDPROCESSINGML_URI = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WORD_SHAPE_URI = "http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
WORD_GROUP_URI = "http://schemas.microsoft.com/office/word/2010/wordprocessingGroup"
WORD_CANVAS_URI = "http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas"
_PICTURE_URI = "http://schemas.openxmlformats.org/drawingml/2006/picture"

DRAWINGML_NS = f"{{{DRAWINGML_URI}}}"
WORD_DRAWING_NS = f"{{{WORD_DRAWING_URI}}}"
WORDPROCESSINGML_NS = f"{{{WORDPROCESSINGML_URI}}}"
WORD_SHAPE_NS = f"{{{WORD_SHAPE_URI}}}"
WORD_GROUP_NS = f"{{{WORD_GROUP_URI}}}"
WORD_CANVAS_NS = f"{{{WORD_CANVAS_URI}}}"

EXT_LST = f"{DRAWINGML_NS}extLst"

_PREFIXES = {
    DRAWINGML_URI: "a",
    WORD_DRAWING_URI: "wp",
    WORDPROCESSINGML_URI: "w",
    WORD_SHAPE_URI: "wps",
    WORD_GROUP_URI: "wpg",
    WORD_CANVAS_URI: "wpc",
    _PICTURE_URI: "pic",
}


def unsupported(reason: str) -> UnsupportedShapeFigure:
    return UnsupportedShapeFigure(reason)


def local_name(element: Element) -> str:
    """The element's name without its namespace (``lnRef`` for ``{uri}lnRef``)."""
    return element.tag.rpartition("}")[2]


def tag_name(element: Element) -> str:
    """The element's prefixed name as Word writes it, for the unsupported reason."""
    namespace = element.tag[1:].partition("}")[0] if element.tag.startswith("{") else ""
    prefix = _PREFIXES.get(namespace)
    return f"{prefix}:{local_name(element)}" if prefix else local_name(element)


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


__all__ = [
    "DRAWINGML_NS",
    "DRAWINGML_URI",
    "EXT_LST",
    "WORDPROCESSINGML_NS",
    "WORDPROCESSINGML_URI",
    "WORD_CANVAS_NS",
    "WORD_CANVAS_URI",
    "WORD_DRAWING_NS",
    "WORD_DRAWING_URI",
    "WORD_GROUP_NS",
    "WORD_GROUP_URI",
    "WORD_SHAPE_NS",
    "WORD_SHAPE_URI",
    "Element",
    "elements",
    "flag",
    "int_attr",
    "int_attr_or",
    "local_name",
    "only",
    "tag_name",
    "unsupported",
]
