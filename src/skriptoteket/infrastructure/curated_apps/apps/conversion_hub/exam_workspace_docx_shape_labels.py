"""Reads the text box label of one Word shape (TASK-SKRIPT-39-04-22, D2, D3).

Purpose:
    ``LabelReader`` reads a shape's ``wps:txbx`` and ``wps:bodyPr`` into a ``ShapeLabel``: the
    paragraphs with their alignment, the runs with text, size, colour, bold, italic and
    underline, and the text box insets and vertical anchor. Run marks and paragraph alignment
    come from the run, its character style chain and the paragraph style chain, strongest first.
    The reader is exact: any element or value the label model does not hold raises
    ``UnsupportedShapeFigure`` (D3).

Relationships:
    - ``exam_workspace_docx_shape_reader`` calls ``LabelReader.read`` for every shape.
    - ``exam_workspace_docx_shape_xml`` holds the namespaces and the exact XML helpers.
    - ``exam_workspace_docx_shape_colors`` resolves the style font colour through the theme.
    - ``exam_workspace_docx_source_format.style_chain`` walks the style ``basedOn`` chain.
"""

from __future__ import annotations

from docx.document import Document as DocxDocument
from docx.oxml.text.paragraph import CT_P
from docx.oxml.text.run import CT_R
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_colors import (  # noqa: E501
    HEX,
    Theme,
    hex_color,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_figure import (  # noqa: E501
    LabelAlign,
    LabelAnchor,
    LabelParagraph,
    LabelRun,
    ShapeLabel,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_shape_xml import (  # noqa: E501
    DRAWINGML_NS,
    EXT_LST,
    WORD_SHAPE_NS,
    WORDPROCESSINGML_NS,
    Element,
    elements,
    flag,
    int_attr_or,
    only,
    tag_name,
    unsupported,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_source_format import (  # noqa: E501
    style_chain,
)

_DEFAULT_SIZE_PT = 10.0
_DEFAULT_INSETS: tuple[int, int, int, int] = (91440, 45720, 91440, 45720)
_ALIGNMENTS: dict[str, LabelAlign] = {
    "left": "left", "start": "left", "center": "center", "right": "right", "end": "right",
    "both": "justify",
}  # fmt: skip
_ANCHORS: dict[str, LabelAnchor] = {"t": "t", "ctr": "ctr", "b": "b"}
_PARAGRAPH_CHILDREN = frozenset(
    f"{WORDPROCESSINGML_NS}{name}"
    for name in ("pPr", "r", "bookmarkStart", "bookmarkEnd", "proofErr")
)
_RUN_CHILDREN = frozenset(
    f"{WORDPROCESSINGML_NS}{name}"
    for name in ("rPr", "t", "tab", "br", "cr", "noBreakHyphen", "lastRenderedPageBreak")
)
# Direct or inherited run marks that change what Word draws and that the label model lacks.
_UNMODELLED_MARKS = ("strike", "dstrike", "highlight", "shd", "vertAlign", "caps", "smallCaps")
_MARK_OFF = frozenset({"0", "false", "off", "none", "baseline"})


class LabelReader:
    """Reads the labels of one drawing's shapes; shares the drawing's theme."""

    def __init__(self, document: DocxDocument, theme: Theme) -> None:
        self._document = document
        self._theme = theme

    def read(self, children: list[Element], style: dict[str, Element]) -> ShapeLabel | None:
        """Read the label of a ``wps:wsp`` from its children; None when it shows no text.

        ``style`` holds the shape's ``wps:style`` references by local name; ``fontRef`` gives
        the colour of runs set to ``auto``.
        """
        text_box = next((c for c in children if c.tag == f"{WORD_SHAPE_NS}txbx"), None)
        if text_box is None:
            return None
        content = only(text_box, frozenset({f"{WORDPROCESSINGML_NS}txbxContent"}))
        if not content:
            return None
        paragraphs = [
            self._paragraph(p, style)
            for p in only(content[0], frozenset({f"{WORDPROCESSINGML_NS}p"}))
        ]
        body = next((c for c in children if c.tag == f"{WORD_SHAPE_NS}bodyPr"), None)
        insets, anchor = self._body(body)
        if not any(run.text for paragraph in paragraphs for run in paragraph.runs):
            return None
        return ShapeLabel(tuple(paragraphs), *insets, anchor=anchor)

    @staticmethod
    def _body(body: Element | None) -> tuple[tuple[int, int, int, int], LabelAnchor]:
        if body is None:
            return _DEFAULT_INSETS, "t"
        anchor_name = body.get("anchor", "t")
        anchor = _ANCHORS.get(anchor_name)
        if anchor is None:
            raise unsupported(f"wps:bodyPr anchor {anchor_name!r}")
        if body.get("vert", "horz") != "horz" or int_attr_or(body, "rot", 0) != 0:
            raise unsupported("wps:bodyPr with vertical or rotated text")
        if int_attr_or(body, "numCol", 1) != 1 or flag(body, "upright") or flag(body, "anchorCtr"):
            raise unsupported("wps:bodyPr with columns, upright or centred text")
        for fit in elements(body):
            if fit.tag in (f"{DRAWINGML_NS}noAutofit", f"{DRAWINGML_NS}spAutoFit", EXT_LST):
                continue
            if fit.tag == f"{DRAWINGML_NS}normAutofit" and not fit.attrib:
                continue
            # Word writes "no text warp" into every text box it saves.
            if fit.tag == f"{DRAWINGML_NS}prstTxWarp" and fit.get("prst") == "textNoShape":
                continue
            raise unsupported(f"{tag_name(fit)} in wps:bodyPr")
        left, top, right, bottom = _DEFAULT_INSETS
        insets = (
            int_attr_or(body, "lIns", left),
            int_attr_or(body, "tIns", top),
            int_attr_or(body, "rIns", right),
            int_attr_or(body, "bIns", bottom),
        )
        return insets, anchor

    def _paragraph(self, p: Element, style: dict[str, Element]) -> LabelParagraph:
        if not isinstance(p, CT_P):
            raise unsupported(f"{tag_name(p)} in a label that is not a w:p paragraph")
        children = only(p, _PARAGRAPH_CHILDREN)
        paragraph = Paragraph(p, self._document)
        properties = p.find(f"{WORDPROCESSINGML_NS}pPr")
        numbering = None if properties is None else properties.find(f"{WORDPROCESSINGML_NS}numPr")
        if numbering is not None:
            number = numbering.find(f"{WORDPROCESSINGML_NS}numId")
            if number is None or number.get(f"{WORDPROCESSINGML_NS}val") != "0":
                raise unsupported("w:numPr in a label paragraph")
        runs = [
            self._run(r, paragraph, style) for r in children if r.tag == f"{WORDPROCESSINGML_NS}r"
        ]
        return LabelParagraph(tuple(run for run in runs if run.text), self._alignment(p, paragraph))

    @staticmethod
    def _alignment(p: Element, paragraph: Paragraph) -> LabelAlign:
        sources = [p, *(s.element for s in style_chain(paragraph.style))]
        for source in sources:
            properties = source.find(f"{WORDPROCESSINGML_NS}pPr")
            justification = (
                None if properties is None else properties.find(f"{WORDPROCESSINGML_NS}jc")
            )
            if justification is not None:
                value = justification.get(f"{WORDPROCESSINGML_NS}val") or ""
                if value not in _ALIGNMENTS:
                    raise unsupported(f"w:jc {value!r}")
                return _ALIGNMENTS[value]
        return "left"

    def _run(self, r: Element, paragraph: Paragraph, style: dict[str, Element]) -> LabelRun:
        parts = only(r, _RUN_CHILDREN)
        marks = self._marks(r, paragraph)
        text = ""
        for part in parts:
            if part.tag == f"{WORDPROCESSINGML_NS}t":
                text += part.text or ""
            elif part.tag == f"{WORDPROCESSINGML_NS}tab":
                text += " "
            elif part.tag == f"{WORDPROCESSINGML_NS}noBreakHyphen":
                text += "-"
            elif part.tag in (f"{WORDPROCESSINGML_NS}br", f"{WORDPROCESSINGML_NS}cr"):
                if part.get(f"{WORDPROCESSINGML_NS}type", "textWrapping") != "textWrapping":
                    raise unsupported(f"w:br type {part.get(f'{WORDPROCESSINGML_NS}type')!r}")
                text += "\n"
        for mark in (*_UNMODELLED_MARKS, "vanish"):
            active = self._first(marks, mark)
            if (
                text
                and active is not None
                and active.get(f"{WORDPROCESSINGML_NS}val") not in _MARK_OFF
            ):
                raise unsupported(f"w:{mark} on a label run")
        underline = self._first(marks, "u")
        return LabelRun(
            text=text,
            size_pt=self._size(marks),
            color=self._text_color(marks, style),
            bold=self._toggle(marks, "b"),
            italic=self._toggle(marks, "i"),
            underline=underline is not None
            and underline.get(f"{WORDPROCESSINGML_NS}val", "single") != "none",
        )

    def _marks(self, r: Element, paragraph: Paragraph) -> list[Element]:
        """The ``w:rPr`` that apply to a run, strongest first: run, its styles, paragraph styles."""
        if not isinstance(r, CT_R):
            raise unsupported(f"{tag_name(r)} in a label that is not a w:r run")
        run = Run(r, paragraph)
        sources = [
            r,
            *(s.element for s in style_chain(run.style)),
            *(s.element for s in style_chain(paragraph.style)),
        ]
        return [
            rpr
            for source in sources
            if (rpr := source.find(f"{WORDPROCESSINGML_NS}rPr")) is not None
        ]

    @staticmethod
    def _first(marks: list[Element], tag: str) -> Element | None:
        return next(
            (m for rpr in marks if (m := rpr.find(f"{WORDPROCESSINGML_NS}{tag}")) is not None), None
        )

    def _toggle(self, marks: list[Element], tag: str) -> bool:
        mark = self._first(marks, tag)
        if mark is None:
            return False
        value = mark.get(f"{WORDPROCESSINGML_NS}val", "1")
        if value in ("1", "true", "on"):
            return True
        if value in ("0", "false", "off"):
            return False
        raise unsupported(f"w:{tag} w:val={value!r}")

    def _size(self, marks: list[Element]) -> float:
        size = self._first(marks, "sz")
        if size is None:
            styles = self._document.styles.element
            size = styles.find(
                f"{WORDPROCESSINGML_NS}docDefaults/{WORDPROCESSINGML_NS}rPrDefault/{WORDPROCESSINGML_NS}rPr/{WORDPROCESSINGML_NS}sz"
            )
        return _DEFAULT_SIZE_PT if size is None else _int_w(size) / 2

    def _text_color(self, marks: list[Element], style: dict[str, Element]) -> str:
        color = self._first(marks, "color")
        if color is not None:
            value = color.get(f"{WORDPROCESSINGML_NS}val") or ""
            # With a w:themeColor Word still stores the resolved colour in w:val.
            if value == "auto" and color.get(f"{WORDPROCESSINGML_NS}themeColor") is not None:
                raise unsupported("w:color/@w:themeColor without a resolved w:val")
            if value != "auto":
                if not HEX.fullmatch(value):
                    raise unsupported(f"w:color {value!r}")
                return value.upper()
        font_color = self._theme.reference_color(style.get("fontRef"))
        return "000000" if font_color is None else hex_color(font_color)


def _int_w(element: Element) -> int:
    value = element.get(f"{WORDPROCESSINGML_NS}val")
    try:
        return int(value or "")
    except ValueError:
        raise unsupported(f"{tag_name(element)} w:val={value!r}") from None


__all__ = ["LabelReader"]
