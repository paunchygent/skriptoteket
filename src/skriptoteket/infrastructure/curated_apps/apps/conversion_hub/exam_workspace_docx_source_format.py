"""Read a DOCX document's kept source formatting: run marks and paragraph heading levels.

Marks
    A run's marks are ``bold``, ``italic``, ``underline``, ``superscript`` and
    ``subscript``, always in that order. Each mark resolves the way Word renders it: the
    run's direct font formatting decides first, then its character-style chain, then the
    paragraph-style chain, then the document defaults. The first source that states the
    property decides, so an explicit False cancels an inherited mark. Superscript and
    subscript are one ``w:vertAlign`` property and resolve as one value: a direct
    baseline cancels an inherited script mark, and a run is never both.

Heading levels
    A paragraph styled ``Title`` is level 1 and paragraphs styled ``Heading 1`` to
    ``Heading 3`` are levels 1-3. Otherwise a whole paragraph is a heading only when
    every non-whitespace run is larger than the document's body size; the smallest such
    run size gives the ratio to the body size, and 1.8 or more is level 1, 1.5 or more
    level 2, 1.25 or more level 3. A run whose size cannot be resolved counts as body
    size, so a larger word inside body-sized text never makes a heading.

Body size
    The body size is the effective point size carried by the most non-whitespace
    characters across all paragraphs that are not styled as headings, ties going to the
    smaller size. When no run states a size, the Normal style's size applies, else 11 pt.
"""

from collections.abc import Iterator
from typing import NamedTuple

from docx.document import Document as DocxDocument
from docx.enum.text import WD_UNDERLINE
from docx.oxml.ns import qn
from docx.oxml.simpletypes import ST_OnOff
from docx.oxml.table import CT_Tbl
from docx.oxml.text.font import CT_RPr
from docx.oxml.text.paragraph import CT_P
from docx.styles.style import CharacterStyle, ParagraphStyle
from docx.table import Table, _Cell
from docx.text.font import Font
from docx.text.hyperlink import Hyperlink
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxSourceParagraph,
    DocxSourceRun,
)

_FALLBACK_BODY_POINTS = 11.0
_HEADING_STYLES = {"Title": 1, "Heading 1": 1, "Heading 2": 2, "Heading 3": 3}
_SIZE_HEADING_LEVELS = ((1.8, 1), (1.5, 2), (1.25, 3))


class _FontState(NamedTuple):
    """One formatting source's values; None means the source states nothing about it."""

    bold: bool | None
    italic: bool | None
    underline: bool | None
    vertical: str | None
    size: float | None


def paragraph_run_spans(paragraph: Paragraph) -> tuple[tuple[Run, int, str], ...]:
    """Every run's text and its offset inside the paragraph's own text, in order.

    Hyperlink runs are runs, and the offset counts the earlier runs' ``text``, so these
    spans tile the paragraph text exactly like ``Paragraph.text``.
    """
    spans: list[tuple[Run, int, str]] = []
    cursor = 0
    for content in paragraph.iter_inner_content():
        runs = content.runs if isinstance(content, Hyperlink) else (content,)
        for run in runs:
            text = run.text
            spans.append((run, cursor, text))
            cursor += len(text)
    return tuple(spans)


def source_run(
    run: Run, paragraph: Paragraph, document: DocxDocument, *, offset: int
) -> DocxSourceRun:
    """One run's text and kept marks, placed at ``offset`` in its chunk's plain text."""
    return DocxSourceRun(offset=offset, text=run.text, marks=run_marks(run, paragraph, document))


def run_marks(run: Run, paragraph: Paragraph, document: DocxDocument) -> tuple[str, ...]:
    """The run's kept marks, in the canonical order bold, italic, underline, sup, sub."""
    state = _merged_state(run, paragraph, document)
    return tuple(
        mark
        for mark, active in (
            ("bold", state.bold),
            ("italic", state.italic),
            ("underline", state.underline),
            ("superscript", state.vertical == "superscript"),
            ("subscript", state.vertical == "subscript"),
        )
        if active
    )


def effective_run_points(run: Run, paragraph: Paragraph, document: DocxDocument) -> float | None:
    """The run's effective font size in points, or None when no source states one."""
    return _merged_state(run, paragraph, document).size


def source_paragraph(
    paragraph: Paragraph, document: DocxDocument, *, body_points: float
) -> DocxSourceParagraph:
    """One paragraph's own text and heading level, with offsets relative to that text."""
    return DocxSourceParagraph(
        offset=0,
        text="".join(text for _, _, text in paragraph_run_spans(paragraph)),
        heading_level=paragraph_heading_level(paragraph, document, body_points=body_points),
    )


def paragraph_heading_level(
    paragraph: Paragraph, document: DocxDocument, *, body_points: float
) -> int | None:
    """The paragraph's heading level 1-3, else None, by style first and size second."""
    by_style = _HEADING_STYLES.get(_style_name(paragraph))
    if by_style is not None:
        return by_style
    smallest: float | None = None
    for run, _, text in paragraph_run_spans(paragraph):
        if not text.strip():
            continue
        size = effective_run_points(run, paragraph, document)
        if size is None:
            return None
        smallest = size if smallest is None else min(smallest, size)
    if smallest is None or smallest <= body_points:
        return None
    ratio = smallest / body_points
    for threshold, level in _SIZE_HEADING_LEVELS:
        if ratio >= threshold:
            return level
    return None


def document_body_points(document: DocxDocument) -> float:
    """The document's body size in points, weighted by non-whitespace characters.

    Paragraphs styled Title or Heading 1-3 are excluded, so heading sizes never define
    the body. Size ties go to the smaller size. Without any stated run size the Normal
    style's size applies, else 11 pt.
    """
    weights: dict[float, int] = {}
    for paragraph in _document_paragraphs(document):
        if _HEADING_STYLES.get(_style_name(paragraph)) is not None:
            continue
        for run, _, text in paragraph_run_spans(paragraph):
            count = sum(1 for character in text if not character.isspace())
            if not count:
                continue
            points = effective_run_points(run, paragraph, document)
            if points is None:
                continue
            weights[points] = weights.get(points, 0) + count
    if weights:
        return min(weights.items(), key=lambda item: (-item[1], item[0]))[0]
    normal = _normal_points(document)
    return normal if normal is not None else _FALLBACK_BODY_POINTS


def _merged_state(run: Run, paragraph: Paragraph, document: DocxDocument) -> _FontState:
    """The run's effective state: direct, character styles, paragraph styles, defaults."""
    states: list[_FontState] = [_font_state(run.font)]
    states.extend(_font_state(style.font) for style in style_chain(run.style))
    states.extend(_font_state(style.font) for style in style_chain(paragraph.style))
    states.append(_defaults_state(document))
    bold: bool | None = None
    italic: bool | None = None
    underline: bool | None = None
    vertical: str | None = None
    size: float | None = None
    for state in states:
        if bold is None:
            bold = state.bold
        if italic is None:
            italic = state.italic
        if underline is None:
            underline = state.underline
        if vertical is None:
            vertical = state.vertical
        if size is None:
            size = state.size
    return _FontState(bold, italic, underline, vertical, size)


def _font_state(font: Font) -> _FontState:
    size = font.size
    return _FontState(
        bold=font.bold,
        italic=font.italic,
        underline=_underline_state(font.underline),
        vertical=_vertical(font.superscript, font.subscript),
        size=size.pt if size is not None else None,
    )


def style_chain(
    style: CharacterStyle | ParagraphStyle | None,
) -> Iterator[CharacterStyle | ParagraphStyle]:
    """Yield a style and its bases; Word ignores a basedOn cycle, so stop at a repeat."""
    seen: set[str | None] = set()
    while style is not None and style.style_id not in seen:
        seen.add(style.style_id)
        yield style
        style = style.base_style


def _defaults_state(document: DocxDocument) -> _FontState:
    """The document-default run properties, or nothing when the styles part has none."""
    rpr = _defaults_rpr(document)
    if rpr is None:
        return _FontState(None, None, None, None, None)
    size = rpr.sz_val
    return _FontState(
        bold=_rpr_toggle(rpr, "w:b"),
        italic=_rpr_toggle(rpr, "w:i"),
        underline=_underline_state(rpr.u_val),
        vertical=_vertical(rpr.superscript, rpr.subscript),
        size=size.pt if size is not None else None,
    )


def _defaults_rpr(document: DocxDocument) -> CT_RPr | None:
    defaults = document.styles.element.find(qn("w:docDefaults"))
    if defaults is None:
        return None
    rpr_default = defaults.find(qn("w:rPrDefault"))
    if rpr_default is None:
        return None
    rpr = rpr_default.find(qn("w:rPr"))
    return rpr if isinstance(rpr, CT_RPr) else None


def _rpr_toggle(rpr: CT_RPr, tag: str) -> bool | None:
    """A ``w:b``-style on/off child's value, None when the child is absent."""
    toggle = rpr.find(qn(tag))
    if toggle is None:
        return None
    value = toggle.get(qn("w:val"))
    return True if value is None else bool(ST_OnOff.from_xml(value))


def _underline_state(value: bool | WD_UNDERLINE | None) -> bool | None:
    """True for any underline style, False for an explicit none, None when inherited."""
    if value is None or value is WD_UNDERLINE.INHERITED:
        return None
    if value is True:
        return True
    if value is False or value is WD_UNDERLINE.NONE:
        return False
    return True


def _vertical(superscript: bool | None, subscript: bool | None) -> str | None:
    """One ``w:vertAlign`` decision: superscript, subscript, baseline or inherited."""
    if superscript:
        return "superscript"
    if subscript:
        return "subscript"
    if superscript is False or subscript is False:
        return "baseline"
    return None


def _style_name(paragraph: Paragraph) -> str:
    style = paragraph.style
    return style.name if style is not None else ""


def _normal_points(document: DocxDocument) -> float | None:
    """The Normal style's own font size, or None when it states none."""
    try:
        style = document.styles["Normal"]
    except KeyError:
        return None
    size = style.font.size
    return size.pt if size is not None else None


def _document_paragraphs(document: DocxDocument) -> Iterator[Paragraph]:
    """Every body paragraph in document order, table cells and nested tables included."""
    for element in document.element.body:
        if isinstance(element, CT_P):
            yield Paragraph(element, document)
        elif isinstance(element, CT_Tbl):
            yield from _table_paragraphs(Table(element, document), document)


def _table_paragraphs(table: Table, document: DocxDocument) -> Iterator[Paragraph]:
    """Every paragraph of the table's cells in row order, nested tables included.

    Raw ``tc`` elements are walked exactly like the chunker walks them, so a merged
    cell's text is counted once and these sizes match the text the chunker renders.
    """
    for row in table.rows:
        for element in row._tr.tc_lst:
            cell = _Cell(element, table)
            for block in cell.iter_inner_content():
                if isinstance(block, Paragraph):
                    yield block
                else:
                    yield from _table_paragraphs(block, document)
