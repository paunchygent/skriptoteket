"""Lay out one text PDF's words as lines and ruled tables in reading order (ST-SKRIPT-39-10).

Each page's words, with their font size and bold or italic font, group into visual lines.
A page whose words leave a clear gutter near the middle reads the left column, then the
right, between any full-width lines. Ruled tables found by pdfplumber keep their cells; a
single ruled box is a bordered paragraph, not a table, and reads as lines. A line at the
top or bottom of the page that recurs at the same place on most pages (a header or
footer) and a page number there (``3``, ``Sida 3 av 5``) are dropped. Vector graphics,
such as drawn answer lines, carry no text and never become a line.

Relationships:
    ``exam_workspace_pdf_blocks`` turns the laid-out lines and tables into Word-shaped
    chunks; ``exam_workspace_pdf_chunker`` opens the PDF and calls both.
"""

from __future__ import annotations

import re
import statistics
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

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
# other number stays significant, so a prompt naming another page is ordinary text. Such
# a line must also sit apart from the body text: in a font smaller than the body text by
# more than this many points, or separated from the body block by more white space than
# one body line step. "Uppgift 2" at body size at the top of page 2 is a question.
_SMALLER_POINTS = 0.6
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


PdfItem = PdfLine | PdfTable


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
    laid_out = [_page_items(page, index, words[index], margins) for index, page in enumerate(pages)]
    kept = _without_page_furniture(
        [items for _, items in laid_out], [height for height, _ in laid_out]
    )
    return [item for items in kept for item in items]


# --- Page reading -------------------------------------------------------------------------


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
    page: Page, page_index: int, words: Sequence[PdfWord], margins: tuple[float, float]
) -> tuple[float, list[PdfItem]]:
    """One page's lines and tables in reading order, with the page height.

    A line's edges are its column's: the document's text margins for a full-width line
    and the outer side of a column, the gutter's sides for the inner side.
    """
    tables = [table for table in page.find_tables() if _cell_count(table) > 1]
    table_boxes = [_bbox(table.bbox) for table in tables]
    body = [word for word in words if not any(_inside(word, box) for box in table_boxes)]
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
    if isinstance(item, PdfLine):
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


def _apart_from_body(
    line: PdfLine,
    page: Sequence[PdfItem],
    height: float,
    body: float,
    pitch: float,
) -> bool:
    """A smaller font than the body text, or more than a body line step of white space
    between the line and the nearest text toward the middle of the page. Text in the
    opposite band is no body text, so a page with no body between keeps the line."""
    if body == 0.0:
        return False
    if line.size < body - _SMALLER_POINTS:
        return True
    others = [item for item in page if item is not line]
    if line.top < height / 2:
        below = [
            _item_top(item)
            for item in others
            if line.top < _item_top(item) < height * (1 - _FURNITURE_BAND)
        ]
        return bool(below) and min(below) - line.bottom > pitch
    above = [
        _item_bottom(item)
        for item in others
        if height * _FURNITURE_BAND < _item_bottom(item) and _item_top(item) < line.top
    ]
    return bool(above) and line.top - max(above) > pitch


def _apart_on_every_page(
    seen: Sequence[tuple[int, float, tuple[int, ...], PdfLine]],
    pages: Sequence[Sequence[PdfItem]],
    heights: Sequence[float],
) -> bool:
    body, pitch = _body_size_and_pitch(pages, frozenset(id(line) for _, _, _, line in seen))
    return all(
        _apart_from_body(line, pages[page - 1], heights[page - 1], body, pitch)
        for page, _, _, line in seen
    )


def _numbers_constant(seen: Sequence[tuple[int, float, tuple[int, ...], PdfLine]]) -> bool:
    """The occurrences carry the same numbers, so the line repeats word for word."""
    return len({numbers for _, _, numbers, _ in seen}) == 1


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
    same value on every page or matches the page the line sits on; any other changing
    number keeps the line as ordinary text on every page.
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
        and (_numbers_constant(seen) or _apart_on_every_page(seen, pages, heights))
    }
    dropped = {
        id(line)
        for lines in candidates
        for line in lines
        if _line_shape(line) in repeated or _PAGE_NUMBER.fullmatch(line.text.strip())
    }
    return [[item for item in items if id(item) not in dropped] for items in pages]
