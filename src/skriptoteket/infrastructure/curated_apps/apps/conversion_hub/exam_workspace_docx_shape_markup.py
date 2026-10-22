"""Self-contained markup of a Word drawing, kept for Word export (D8, D12)."""

import copy

from docx.oxml.ns import qn
from docx.oxml.xmlchemy import BaseOxmlElement
from lxml import etree  # type: ignore[import-untyped]  # transitive of python-docx, no stubs

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


def self_contained_shapes(drawing: BaseOxmlElement) -> str | None:
    """The ``w:drawing`` as standalone XML, or None when it needs another part.

    A relationship attribute (picture embed or link, hyperlink id) or a footnote,
    endnote, comment, object or pict element ties the drawing to the source package, so
    it cannot be rebuilt elsewhere. Otherwise every namespace the subtree uses is
    declared on the serialized root; the source tree stays untouched and ids are kept.
    """
    for element in drawing.iter():
        if element.tag in _OTHER_PART_TAGS:
            return None
        if any(
            isinstance(name, str) and name.startswith(_RELATIONSHIPS_NS) for name in element.attrib
        ):
            return None
    markup: str = etree.tostring(copy.deepcopy(drawing), encoding="unicode")
    return markup
