"""Drop a text PDF's page furniture: headers, footers, page numbers, logos (ST-SKRIPT-39-10).

A line at the top or bottom of the page that recurs at the same place on most pages (a
header or footer) and a page number there (``3``, ``Sida 3 av 5``) are dropped, as is a
picture region recurring there (a header logo).

Relationships:
    ``exam_workspace_pdf_layout`` calls ``without_page_furniture`` on every page's
    laid-out items and reads ``FURNITURE_BAND`` to leave the bands out of its column
    search; ``exam_workspace_pdf_items`` holds the item types.
"""

from __future__ import annotations

import re
import statistics
from collections import Counter
from collections.abc import Sequence

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_items import (  # noqa: E501
    PdfItem,
    PdfLine,
    PdfPictureRegion,
    item_bottom,
    item_top,
)

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
FURNITURE_BAND = 0.12
_FURNITURE_LINES = 2
_FURNITURE_PLACE_POINTS = 2.0


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
        tops.append(min(item_top(item) for item in items) / height)
        bottoms.append(max(item_bottom(item) for item in items) / height)
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
    lines = sorted((item for item in items if isinstance(item, PdfLine)), key=item_top)
    ends = [*lines[:_FURNITURE_LINES], *lines[-_FURNITURE_LINES:]]
    return [
        line
        for line in dict.fromkeys(ends)
        if line.bottom <= height * FURNITURE_BAND or line.top >= height * (1 - FURNITURE_BAND)
    ]


def without_page_furniture(
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
        and (item.bottom <= height * FURNITURE_BAND or item.top >= height * (1 - FURNITURE_BAND))
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
