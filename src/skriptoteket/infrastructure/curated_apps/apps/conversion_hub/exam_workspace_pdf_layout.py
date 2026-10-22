"""Lay out one text PDF's words as lines and ruled tables in reading order (ST-SKRIPT-39-10).

A page whose words leave a clear gutter near the middle reads the left column, then the
right, between any full-width lines. A single ruled box is a bordered paragraph, not a
table, and reads as lines, and a ruled grid without text is a drawing. Placed pictures
and figures drawn with lines become picture regions at their place in the reading order;
a figure's labels belong to its region and are not read as lines. Drawn answer lines,
rules and frames carry no text and become neither a line nor a picture.

Relationships:
    ``exam_workspace_pdf_page_adapter`` reads each page's pdfplumber objects;
    ``exam_workspace_pdf_graphics`` decides each page's picture regions from that
    geometry; ``exam_workspace_pdf_furniture`` drops headers, footers and page numbers;
    ``exam_workspace_pdf_pictures`` cuts the regions out of the rendered pages;
    ``exam_workspace_pdf_blocks`` turns the laid-out items into Word-shaped chunks;
    ``exam_workspace_pdf_chunker`` opens the PDF and calls them.
"""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from typing import TYPE_CHECKING

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_furniture import (  # noqa: E501
    FURNITURE_BAND,
    without_page_furniture,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_graphics import (  # noqa: E501
    Box,
    page_cuts,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_items import (  # noqa: E501
    PdfItem,
    PdfLine,
    PdfPictureRegion,
    PdfWord,
    body_points,
    item_top,
    raw_lines,
    word_inside,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_page_adapter import (  # noqa: E501
    cell_count,
    float_box,
    page_graphics,
    read_words,
    table_item,
)

if TYPE_CHECKING:
    from pdfplumber.page import Page

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


def read_pages(pages: Sequence[Page]) -> list[PdfItem]:
    """Every page's lines and tables in reading order, page furniture dropped.

    Full-width lines and the columns' outer sides share the document's text margins, so a
    page of short lines still measures its wraps against the real line width.
    """
    words = [read_words(page) for page in pages]
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
    kept = without_page_furniture(
        [items for _, items in laid_out], [height for height, _ in laid_out]
    )
    return [item for items in kept for item in items]


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
        if height * FURNITURE_BAND < (word.top + word.bottom) / 2 < height * (1 - FURNITURE_BAND)
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


def _overlaps(first: Box, second: Box) -> bool:
    """Two boxes share an area: touching edges do not overlap."""
    return (
        first[0] < second[2]
        and second[0] < first[2]
        and first[1] < second[3]
        and second[1] < first[3]
    )


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
        if cell_count(table) > 1 and any(word_inside(word, float_box(table.bbox)) for word in words)
    ]
    table_boxes = [float_box(table.bbox) for table in tables]
    cuts = page_cuts(page_graphics(page, words, table_boxes, margins[0]), body_size=body_size)
    labels = {position for cut in cuts for position in cut.labels}
    body = [
        word
        for position, word in enumerate(words)
        if position not in labels and not any(word_inside(word, box) for box in table_boxes)
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
        items.append(table_item(table, box, words, page_index, column_of(box[0], box[2])))
    visible = (
        float(page.cropbox[0]),
        float(page.cropbox[1]),
        float(page.cropbox[2]),
        float(page.cropbox[3]),
    )
    mapped = page.rotation == 0
    for cut in cuts:
        x0, top, x1, bottom = cut.box
        clipped = (
            max(x0, visible[0]),
            max(top, visible[1]),
            min(x1, visible[2]),
            min(bottom, visible[3]),
        )
        column = column_of(clipped[0], clipped[2])
        erase = tuple(
            (word.x0, word.top, word.x1, word.bottom)
            for position, word in enumerate(words)
            if position not in cut.labels
            and _overlaps((word.x0, word.top, word.x1, word.bottom), clipped)
        )
        items.append(
            PdfPictureRegion(
                page_index,
                column,
                cut.kind,
                clipped[0],
                clipped[1],
                clipped[2],
                clipped[3],
                visible,
                mapped,
                erase,
            )
        )
    return float(page.height), _reading_order(items)


def _reading_order(items: list[PdfItem]) -> list[PdfItem]:
    """Full-width items top to bottom; between two of them, the left column then the right."""
    spanning = sorted((item for item in items if item.column == 0), key=item_top)
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
