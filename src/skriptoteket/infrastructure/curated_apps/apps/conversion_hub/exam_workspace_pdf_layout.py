"""Lay out one text PDF's words as lines and ruled tables in reading order (ST-SKRIPT-39-10).

Each page's words, with their font size and bold or italic font, group into visual lines.
A page whose words leave a clear gutter near the middle reads the left column, then the
right, between any full-width lines. Ruled tables found by pdfplumber keep their cells; a
single ruled box is a bordered paragraph, not a table, and reads as lines, and a ruled
grid without text is a drawing. Placed pictures and figures drawn with lines become
picture regions at their place in the reading order; a figure's labels belong to its
region and are not read as lines. A line at the top or bottom of the page that recurs
at the same place on most pages (a header or footer) and a page number there (``3``,
``Sida 3 av 5``) are dropped, as is a picture region recurring there (a header logo).
Drawn answer lines, rules and frames carry no text and become neither a line nor a
picture.

Relationships:
    ``exam_workspace_pdf_graphics`` decides each page's picture regions from the
    geometry this module reads; ``exam_workspace_pdf_pictures`` cuts them out of the
    rendered pages; ``exam_workspace_pdf_blocks`` turns the laid-out items into
    Word-shaped chunks; ``exam_workspace_pdf_chunker`` opens the PDF and calls them.
"""

from __future__ import annotations

import re
import statistics
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_graphics import (  # noqa: E501
    Box,
    PageGraphics,
    PdfStroke,
    page_cuts,
)

if TYPE_CHECKING:
    from pdfplumber.page import Page

_BOLD = re.compile(r"bold|black|heavy|semibold|demibold", re.IGNORECASE)
_ITALIC = re.compile(r"italic|oblique", re.IGNORECASE)
_SUBSET_PREFIX = re.compile(r"^[A-Z]{6}\+")
_PAGE_NUMBER = re.compile(
    r"^(?:(?:sida|page|s\.)\s*)?[-–]?\s*\d{1,3}\s*[-–]?"
    r"(?:\s*(?:av|of|/)\s*\d{1,3}|\s*\(\s*\d{1,3}\s*\))?$",
    re.IGNORECASE,
)
_DIGITS = re.compile(r"\d+")
# A repeated line's changing number reads as pagination only when it matches the page
# the line sits on: the 1-based page index, wherever in the line the number sits. Every
# other number stays significant, so a prompt naming another page is ordinary text. A
# repeated line is furniture only when it is also clearly set apart from the body text:
# in a font smaller than the body text by more than this many points, or in the page
# margin, beyond the body text's edge by more white space than one body line step. When
# the reader cannot tell, it keeps the line: a stray header in a question is harmless, a
# dropped question is lost.
_SMALLER_POINTS = 0.6
# At body size, a page-matching number is a page counter only in pagination wording: after
# "sida", "s.", "page" or "p.", or as the N of "N av M" / "N of M". A bare number, as in
# "Uppgift 3" or a lone "3", stays text: a stray page number is harmless, a lost heading
# is not.
_COUNTER_BEFORE = re.compile(r"(?:\bsida|\bs\.|\bpage|\bp\.)\s*$", re.IGNORECASE)
_COUNTER_AFTER = re.compile(r"^\s*(?:av|of)\s+\d", re.IGNORECASE)
_DEFAULT_PITCH_RATIO = 1.35

# Page-furniture band: the outer share of the page height where headers and footers sit,
# how many lines at each end of a page are candidates, and how far a repeated line's place
# may move between pages.
_FURNITURE_BAND = 0.12
_FURNITURE_LINES = 2
_FURNITURE_PLACE_POINTS = 2.0
# Two columns: the gutter lies in the middle share of the text width and is at least this
# wide (or this many font sizes); each side holds at least this share of the page's
# characters, and at least half the left column's lines end within this share of its
# width from the gutter.
_GUTTER_SEARCH = (0.3, 0.7)
_GUTTER_MIN_POINTS = 12.0
_GUTTER_SIZE_RATIO = 1.5
_COLUMN_REACH = 0.2
_COLUMN_MIN_SHARE = 0.25
_COLUMN_MIN_LINES = 3
# Word space: a gap between two words on one line wider than this share of the font size.
WORD_SPACE_RATIO = 0.15
# A colour component this close to white draws nothing visible on white paper.
_WHITE_LEVEL = 0.95
_FALLBACK_BODY_POINTS = 11.0

# A line's column: 0 spans the page (or the page has one column), 1 is left, 2 is right.
FULL_WIDTH = 0


@dataclass(frozen=True)
class PdfWord:
    """One word with its box in points from the page's top-left, size and font marks."""

    text: str
    x0: float
    x1: float
    top: float
    bottom: float
    size: float
    bold: bool
    italic: bool


@dataclass(frozen=True)
class PdfLine:
    """One visual line of one column; its edges are that column's text margins."""

    page: int
    column: int
    words: tuple[PdfWord, ...]
    left_edge: float
    right_edge: float

    @property
    def x0(self) -> float:
        return self.words[0].x0

    @property
    def x1(self) -> float:
        return self.words[-1].x1

    @property
    def top(self) -> float:
        return min(word.top for word in self.words)

    @property
    def bottom(self) -> float:
        return max(word.bottom for word in self.words)

    @property
    def size(self) -> float:
        return max(word.size for word in self.words)

    @property
    def text(self) -> str:
        return joined_words(self.words)


@dataclass(frozen=True)
class PdfTable:
    """One table: ruled, or found from aligned cell starts."""

    page: int
    column: int
    top: float
    rows: tuple[tuple[tuple[PdfLine, ...], ...], ...]
    """Each row's cells; each cell its lines in reading order."""


@dataclass(frozen=True)
class PdfPictureRegion:
    """One placed picture or drawn figure to cut out of its page, with its labels.

    The box is in the page's word coordinates; ``origin`` is the page box's top-left
    corner in them, so the rendered page's pixel grid starts there.
    """

    page: int
    column: int
    kind: Literal["picture", "figure"]
    x0: float
    top: float
    x1: float
    bottom: float
    origin: tuple[float, float]


PdfItem = PdfLine | PdfTable | PdfPictureRegion


def joined_words(words: Sequence[PdfWord]) -> str:
    """One line's words with a space wherever the gap is wider than a word space."""
    parts: list[str] = []
    for index, word in enumerate(words):
        if index and word.x0 - words[index - 1].x1 > word.size * WORD_SPACE_RATIO:
            parts.append(" ")
        parts.append(word.text)
    return "".join(parts)


def read_pages(pages: Sequence[Page]) -> list[PdfItem]:
    """Every page's lines and tables in reading order, page furniture dropped.

    Full-width lines and the columns' outer sides share the document's text margins, so a
    page of short lines still measures its wraps against the real line width.
    """
    words = [_words(page) for page in pages]
    every = [word for page_words in words for word in page_words]
    margins = (
        min((word.x0 for word in every), default=0.0),
        max((word.x1 for word in every), default=0.0),
    )
    body_size = body_points(every)
    laid_out = [
        _page_items(page, index, words[index], margins, body_size)
        for index, page in enumerate(pages)
    ]
    kept = _without_page_furniture(
        [items for _, items in laid_out], [height for height, _ in laid_out]
    )
    return [item for items in kept for item in items]


# --- Page reading -------------------------------------------------------------------------


def body_points(words: Iterable[PdfWord]) -> float:
    """The document's body font size: the most common word size, counted by characters."""
    sizes: Counter[float] = Counter()
    for word in words:
        sizes[round(word.size, 1)] += len(word.text)
    return sizes.most_common(1)[0][0] if sizes else _FALLBACK_BODY_POINTS


def _visible(color: Any) -> bool:
    """A paint colour that shows on white paper: anything but white, in gray, RGB or CMYK.

    A missing colour is PDF's default black; a pattern or named colour counts as visible.
    """
    if color is None:
        return True
    if isinstance(color, (int, float)):
        color = (color,)
    if not isinstance(color, (tuple, list)) or not all(
        isinstance(part, (int, float)) for part in color
    ):
        return True
    if len(color) in (1, 3):
        return not all(part >= _WHITE_LEVEL for part in color)
    if len(color) == 4:
        return not all(part <= 1 - _WHITE_LEVEL for part in color)
    return True


def _page_graphics(
    page: Page,
    words: Sequence[PdfWord],
    tables: Sequence[tuple[float, float, float, float]],
    text_left: float,
) -> PageGraphics:
    """One page's pictures, vector paths, words, visual lines and text tables as boxes."""

    def box(raw: Any) -> Box:
        return (float(raw["x0"]), float(raw["top"]), float(raw["x1"]), float(raw["bottom"]))

    strokes: list[PdfStroke] = []
    kinds: tuple[tuple[Literal["line", "rect", "curve"], Any], ...] = (
        ("line", page.lines),
        ("rect", page.rects),
        ("curve", page.curves),
    )
    for kind, objects in kinds:
        for raw in objects:
            strokes.append(
                PdfStroke(
                    box=box(raw),
                    kind=kind,
                    stroked=bool(raw.get("stroke")) and _visible(raw.get("stroking_color")),
                    filled=bool(raw.get("fill")) and _visible(raw.get("non_stroking_color")),
                )
            )
    index = {id(word): position for position, word in enumerate(words)}
    return PageGraphics(
        width=float(page.width),
        height=float(page.height),
        images=tuple(box(raw) for raw in page.images),
        strokes=tuple(strokes),
        words=tuple((word.x0, word.top, word.x1, word.bottom) for word in words),
        lines=tuple(tuple(index[id(word)] for word in line) for line in raw_lines(words)),
        tables=tuple(tables),
        text_left=text_left,
    )


def _font_marks(fontname: str) -> tuple[bool, bool]:
    name = _SUBSET_PREFIX.sub("", fontname)
    return _BOLD.search(name) is not None, _ITALIC.search(name) is not None


def _words(page: Page) -> list[PdfWord]:
    found: list[PdfWord] = []
    for raw in page.dedupe_chars().extract_words(extra_attrs=["fontname", "size"]):
        bold, italic = _font_marks(str(raw["fontname"]))
        found.append(
            PdfWord(
                text=str(raw["text"]),
                x0=float(raw["x0"]),
                x1=float(raw["x1"]),
                top=float(raw["top"]),
                bottom=float(raw["bottom"]),
                size=float(raw["size"]),
                bold=bold,
                italic=italic,
            )
        )
    return found


def _inside(word: PdfWord, bbox: tuple[float, float, float, float]) -> bool:
    x0, top, x1, bottom = bbox
    middle_x = (word.x0 + word.x1) / 2
    middle_y = (word.top + word.bottom) / 2
    return x0 <= middle_x <= x1 and top <= middle_y <= bottom


def raw_lines(words: Iterable[PdfWord]) -> list[list[PdfWord]]:
    """Words grouped into visual lines by vertical overlap, each line left to right."""
    lines: list[list[PdfWord]] = []
    for word in sorted(words, key=lambda w: (w.top, w.x0)):
        middle = (word.top + word.bottom) / 2
        for line in reversed(lines[-3:]):
            top = min(w.top for w in line)
            bottom = max(w.bottom for w in line)
            if top <= middle <= bottom:
                line.append(word)
                break
        else:
            lines.append([word])
    return [sorted(line, key=lambda w: w.x0) for line in lines]


def _wide_gaps(line: Sequence[PdfWord], low: float, high: float) -> list[tuple[float, float]]:
    """A line's gaps between words that are column-gutter wide and lie in ``low..high``."""
    gaps: list[tuple[float, float]] = []
    for previous, word in zip(line, line[1:], strict=False):
        wide = max(_GUTTER_MIN_POINTS, word.size * _GUTTER_SIZE_RATIO)
        if word.x0 - previous.x1 >= wide and previous.x1 < high and word.x0 > low:
            gaps.append((previous.x1, word.x0))
    return gaps


def _gutter(words: Sequence[PdfWord], height: float) -> tuple[float, float] | None:
    """The x-range of a two-column page's gutter, or None for a single column.

    Lines in the page-furniture bands are left out, since a centred header or page number
    crosses the gutter. A gutter is a wide gap shared by the rows of both columns; each
    side holds a real share of the text, and the left column's lines reach the gutter
    the way wrapped prose does, which a borderless two-part list does not.
    """
    inner = [
        word
        for word in words
        if height * _FURNITURE_BAND < (word.top + word.bottom) / 2 < height * (1 - _FURNITURE_BAND)
    ]
    if not inner:
        return None
    left = min(word.x0 for word in inner)
    right = max(word.x1 for word in inner)
    low = left + (right - left) * _GUTTER_SEARCH[0]
    high = left + (right - left) * _GUTTER_SEARCH[1]
    lines = raw_lines(inner)
    gaps = [gap for line in lines for gap in _wide_gaps(line, low, high)]
    if len(gaps) < _COLUMN_MIN_LINES:
        return None
    # The x-range inside the most gaps: the overlap of the gaps around their median middle.
    middle = statistics.median((x0 + x1) / 2 for x0, x1 in gaps)
    shared = [gap for gap in gaps if gap[0] <= middle <= gap[1]]
    if len(shared) < _COLUMN_MIN_LINES:
        return None
    gutter = (max(x0 for x0, _ in shared), min(x1 for _, x1 in shared))
    if gutter[1] <= gutter[0]:
        return None
    columns = [
        [word for word in inner if word.x1 <= gutter[0]],
        [word for word in inner if word.x0 >= gutter[1]],
    ]
    total = sum(len(word.text) for word in inner)
    for side in columns:
        if sum(len(word.text) for word in side) < total * _COLUMN_MIN_SHARE:
            return None
    left_lines = raw_lines(columns[0])
    column_width = gutter[0] - left
    reaching = [
        line for line in left_lines if line[-1].x1 >= gutter[0] - column_width * _COLUMN_REACH
    ]
    if len(reaching) * 2 < len(left_lines):
        return None
    return gutter


def _crosses(x0: float, x1: float, gutter: tuple[float, float]) -> bool:
    return x0 < gutter[1] and x1 > gutter[0]


def _page_items(
    page: Page,
    page_index: int,
    words: Sequence[PdfWord],
    margins: tuple[float, float],
    body_size: float,
) -> tuple[float, list[PdfItem]]:
    """One page's lines, tables and picture regions in reading order, with the page height.

    A line's edges are its column's: the document's text margins for a full-width line
    and the outer side of a column, the gutter's sides for the inner side. A ruled grid
    with no word in it is no table: its rules reach the picture regions as a drawing.
    """
    tables = [
        table
        for table in page.find_tables()
        if _cell_count(table) > 1 and any(_inside(word, _bbox(table.bbox)) for word in words)
    ]
    table_boxes = [_bbox(table.bbox) for table in tables]
    cuts = page_cuts(_page_graphics(page, words, table_boxes, margins[0]), body_size=body_size)
    labels = {position for cut in cuts for position in cut.labels}
    body = [
        word
        for position, word in enumerate(words)
        if position not in labels and not any(_inside(word, box) for box in table_boxes)
    ]
    gutter = _gutter(body, float(page.height))

    def column_of(x0: float, x1: float) -> int:
        if gutter is None or _crosses(x0, x1, gutter):
            return 0
        return 1 if x1 <= gutter[0] else 2

    left, right = margins
    if gutter is None:
        edges = {0: (left, right)}
    else:
        inner_left = max(w.x1 for w in body if w.x1 <= gutter[0])
        inner_right = min(w.x0 for w in body if w.x0 >= gutter[1])
        edges = {0: (left, right), 1: (left, inner_left), 2: (inner_right, right)}

    items: list[PdfItem] = []
    for raw in raw_lines(body):
        if gutter is not None and any(_crosses(w.x0, w.x1, gutter) for w in raw):
            items.append(PdfLine(page_index, 0, tuple(raw), *edges[0]))
            continue
        for column in (1, 2) if gutter is not None else (0,):
            part = tuple(w for w in raw if gutter is None or column_of(w.x0, w.x1) == column)
            if part:
                items.append(PdfLine(page_index, column, part, *edges[column]))
    for table, box in zip(tables, table_boxes, strict=True):
        items.append(_table_item(table, box, words, page_index, column_of(box[0], box[2])))
    origin = (float(page.bbox[0]), float(page.bbox[1]))
    for cut in cuts:
        x0, top, x1, bottom = cut.box
        column = column_of(x0, x1)
        items.append(PdfPictureRegion(page_index, column, cut.kind, x0, top, x1, bottom, origin))
    return float(page.height), _reading_order(items)


def _bbox(raw: Sequence[float]) -> tuple[float, float, float, float]:
    return (float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3]))


def _cell_count(table: Any) -> int:
    return sum(1 for row in table.rows for cell in row.cells if cell is not None)


def _table_item(
    table: Any,
    box: tuple[float, float, float, float],
    words: Sequence[PdfWord],
    page_index: int,
    column: int,
) -> PdfTable:
    rows: list[tuple[tuple[PdfLine, ...], ...]] = []
    for row in table.rows:
        cells: list[tuple[PdfLine, ...]] = []
        for cell in row.cells:
            if cell is None:
                continue
            bbox = _bbox(cell)
            inside = [word for word in words if _inside(word, bbox)]
            cells.append(
                tuple(
                    PdfLine(page_index, column, tuple(raw), bbox[0], bbox[2])
                    for raw in raw_lines(inside)
                )
            )
        rows.append(tuple(cells))
    return PdfTable(page=page_index, column=column, top=box[1], rows=tuple(rows))


def _item_top(item: PdfItem) -> float:
    return item.top


def _item_bottom(item: PdfItem) -> float:
    if isinstance(item, PdfLine | PdfPictureRegion):
        return item.bottom
    cells = [line.bottom for row in item.rows for cell in row for line in cell]
    return max(cells, default=item.top)


def _reading_order(items: list[PdfItem]) -> list[PdfItem]:
    """Full-width items top to bottom; between two of them, the left column then the right."""
    spanning = sorted((item for item in items if item.column == 0), key=_item_top)
    columns = [item for item in items if item.column != 0]
    ordered: list[PdfItem] = []
    previous = float("-inf")
    for boundary in [*spanning, None]:
        limit = float("inf") if boundary is None else boundary.top
        segment = [item for item in columns if previous <= item.top < limit]
        ordered.extend(sorted(segment, key=lambda item: (item.column, item.top)))
        if boundary is not None:
            ordered.append(boundary)
            previous = boundary.top
    return ordered


# --- Page furniture -----------------------------------------------------------------------


def _line_shape(line: PdfLine) -> str:
    """The normalized line text with every digit run replaced by ``#``.

    Lines with the same shape differ only in their numbers, if at all.
    """
    return _DIGITS.sub("#", " ".join(line.text.lower().split()))


def _line_numbers(line: PdfLine) -> tuple[int, ...]:
    """The line's digit runs as ints, in order."""
    return tuple(int(match) for match in _DIGITS.findall(line.text))


def _numbers_match_pages(
    seen: Sequence[tuple[int, float, tuple[int, ...], PdfLine]],
) -> bool:
    """Every number position is constant or the page number on every occurrence.

    Each tuple holds an occurrence's 1-based page, top, numbers and line. The total in
    "N av M" is constant across pages, so it passes as a constant without any "av/of"
    rule of its own.
    """
    counts = {len(numbers) for _, _, numbers, _ in seen}
    if len(counts) != 1:
        return False
    return all(
        len({numbers[position] for _, _, numbers, _ in seen}) == 1
        or all(numbers[position] == page for page, _, numbers, _ in seen)
        for position in range(next(iter(counts)))
    )


def _body_size_and_pitch(
    pages: Sequence[Sequence[PdfItem]], group: frozenset[int]
) -> tuple[float, float]:
    """The font size of the rest of the document's text (by characters) and its line step,
    the low end of the steps between consecutive lines of that size in one column.

    ``group`` holds the ids of the repeated lines being judged; they are left out.
    """
    sizes: Counter[float] = Counter()
    for items in pages:
        for item in items:
            if isinstance(item, PdfLine) and id(item) not in group:
                for word in item.words:
                    sizes[round(word.size, 1)] += len(word.text)
    if not sizes:
        return 0.0, 0.0
    body = sizes.most_common(1)[0][0]
    steps: list[float] = []
    for items in pages:
        lines = sorted(
            (
                item
                for item in items
                if isinstance(item, PdfLine)
                and id(item) not in group
                and abs(item.size - body) <= _SMALLER_POINTS
            ),
            key=lambda line: (line.column, line.top),
        )
        for previous, line in zip(lines, lines[1:], strict=False):
            if line.column == previous.column and line.top > previous.top:
                steps.append(line.top - previous.top)
    pitch = statistics.quantiles(steps, n=5)[0] if len(steps) >= 4 else body * _DEFAULT_PITCH_RATIO
    return body, pitch


def _body_edges(
    pages: Sequence[Sequence[PdfItem]], heights: Sequence[float], skip: set[int]
) -> tuple[float, float] | None:
    """The body text's top and bottom edge relative to the page height, read from the
    pages in ``skip``'s complement, or None when every page carries the judged line."""
    tops: list[float] = []
    bottoms: list[float] = []
    for page, (items, height) in enumerate(zip(pages, heights, strict=True), start=1):
        if page in skip or not items:
            continue
        tops.append(min(_item_top(item) for item in items) / height)
        bottoms.append(max(_item_bottom(item) for item in items) / height)
    if not tops:
        return None
    return min(tops), max(bottoms)


def _set_apart(
    seen: Sequence[tuple[int, float, tuple[int, ...], PdfLine]],
    pages: Sequence[Sequence[PdfItem]],
    heights: Sequence[float],
) -> bool:
    """Every occurrence is in a smaller font than the body text, or lies in the margin
    beyond the body text's edge, as the pages without the line show it."""
    body, pitch = _body_size_and_pitch(pages, frozenset(id(line) for _, _, _, line in seen))
    if body == 0.0:
        return False
    if all(line.size < body - _SMALLER_POINTS for _, _, _, line in seen):
        return True
    edges = _body_edges(pages, heights, {page for page, _, _, _ in seen})
    if edges is None:
        return False
    top_edge, bottom_edge = edges
    changing = [
        position
        for position in range(len(seen[0][2]))
        if len({numbers[position] for _, _, numbers, _ in seen}) > 1
    ]
    for page, _, _, line in seen:
        height = heights[page - 1]
        if line.size < body - _SMALLER_POINTS:
            continue
        if not all(_counter_form(line, position) for position in changing):
            return False
        if line.top < height / 2:
            if top_edge * height - line.bottom <= pitch:
                return False
        elif line.top - bottom_edge * height <= pitch:
            return False
    return True


def _counter_form(line: PdfLine, position: int) -> bool:
    """The line's ``position``-th number stands in pagination wording."""
    text = " ".join(line.text.split())
    match = list(_DIGITS.finditer(text))[position]
    return (
        _COUNTER_BEFORE.search(text[: match.start()]) is not None
        or _COUNTER_AFTER.match(text[match.end() :]) is not None
    )


def _is_page_number(line: PdfLine, page: int, page_count: int, body: float) -> bool:
    """A lone page number ("3", "Sida 3 av 5") that names the page it sits on, in a
    smaller font than the body text or, at body size, in pagination wording."""
    if _PAGE_NUMBER.fullmatch(line.text.strip()) is None:
        return False
    numbers = _line_numbers(line)
    if numbers[0] != page or any(number != page_count for number in numbers[1:]):
        return False
    return line.size < body - _SMALLER_POINTS or _counter_form(line, 0)


def _furniture_candidates(items: Sequence[PdfItem], height: float) -> list[PdfLine]:
    lines = sorted((item for item in items if isinstance(item, PdfLine)), key=_item_top)
    ends = [*lines[:_FURNITURE_LINES], *lines[-_FURNITURE_LINES:]]
    return [
        line
        for line in dict.fromkeys(ends)
        if line.bottom <= height * _FURNITURE_BAND or line.top >= height * (1 - _FURNITURE_BAND)
    ]


def _without_page_furniture(
    pages: Sequence[Sequence[PdfItem]], heights: Sequence[float]
) -> list[list[PdfItem]]:
    """Drop repeated headers and footers and page numbers at the top and bottom of pages.

    A repeated line is page furniture only when every number position either holds the
    same value on every page or matches the page the line sits on, and the line is set
    apart from the body text (``_set_apart``). Any other line stays text.
    """
    candidates = [_furniture_candidates(items, h) for items, h in zip(pages, heights, strict=True)]
    occurrences: dict[str, list[tuple[int, float, tuple[int, ...], PdfLine]]] = {}
    for index, lines in enumerate(candidates):
        for line in lines:
            occurrences.setdefault(_line_shape(line), []).append(
                (index + 1, line.top, _line_numbers(line), line)
            )
    needed = max(2, (len(pages) + 1) // 2)
    repeated = {
        shape
        for shape, seen in occurrences.items()
        if len({page for page, _, _, _ in seen}) >= needed
        and max(top for _, top, _, _ in seen) - min(top for _, top, _, _ in seen)
        <= _FURNITURE_PLACE_POINTS
        and _numbers_match_pages(seen)
        and _set_apart(seen, pages, heights)
    }
    body, _ = _body_size_and_pitch(pages, frozenset())
    dropped = {
        id(line)
        for page, lines in enumerate(candidates, start=1)
        for line in lines
        if _line_shape(line) in repeated or _is_page_number(line, page, len(pages), body)
    }
    dropped |= _repeated_regions(pages, heights, needed)
    return [[item for item in items if id(item) not in dropped] for items in pages]


def _repeated_regions(
    pages: Sequence[Sequence[PdfItem]], heights: Sequence[float], needed: int
) -> set[int]:
    """Ids of picture regions in the page-furniture band that recur at the same place.

    A header or footer logo prints on every page; Word keeps it in the header part, which
    the Word import never reads, so the PDF import drops it too.
    """
    banded = [
        (page, item)
        for page, (items, height) in enumerate(zip(pages, heights, strict=True))
        for item in items
        if isinstance(item, PdfPictureRegion)
        and (item.bottom <= height * _FURNITURE_BAND or item.top >= height * (1 - _FURNITURE_BAND))
    ]

    def same_place(a: PdfPictureRegion, b: PdfPictureRegion) -> bool:
        return all(
            abs(left - right) <= _FURNITURE_PLACE_POINTS
            for left, right in zip(
                (a.x0, a.top, a.x1, a.bottom), (b.x0, b.top, b.x1, b.bottom), strict=True
            )
        )

    return {
        id(item)
        for _, item in banded
        if len({page for page, other in banded if same_place(item, other)}) >= needed
    }
