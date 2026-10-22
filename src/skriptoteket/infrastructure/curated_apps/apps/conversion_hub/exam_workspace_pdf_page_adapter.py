"""Read one pdfplumber page's objects into typed PDF values (ST-SKRIPT-39-10).

Each word carries its font size and its bold or italic mark, read from the font name. A
ruled table found by pdfplumber keeps its cells, each cell its words as lines. Drawing
and image records become typed boxes; a stroke or fill in a colour that does not show
on white paper draws nothing. A record the adapter cannot read raises
``PdfLayoutError`` naming the missing or non-numeric edge.

Relationships:
    ``exam_workspace_pdf_layout`` calls this module for each page;
    ``exam_workspace_pdf_graphics`` receives the ``PageGraphics`` built here;
    ``exam_workspace_pdf_items`` holds the typed values.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Literal

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_graphics import (  # noqa: E501
    Box,
    PageGraphics,
    PdfStroke,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_items import (  # noqa: E501
    PdfLine,
    PdfTable,
    PdfWord,
    raw_lines,
    word_inside,
)

if TYPE_CHECKING:
    from pdfplumber.page import Page
    from pdfplumber.table import Table

_BOLD = re.compile(r"bold|black|heavy|semibold|demibold", re.IGNORECASE)
_ITALIC = re.compile(r"italic|oblique", re.IGNORECASE)
_SUBSET_PREFIX = re.compile(r"^[A-Z]{6}\+")
# A colour component this close to white draws nothing visible on white paper.
_WHITE_LEVEL = 0.95


_Records = Sequence[Mapping[str, object]]  # pdfplumber drawing or image records


class PdfLayoutError(ValueError):
    """One pdfplumber graphics or table record the typed adapter cannot read."""


def _object_box(raw: Mapping[str, object]) -> Box:
    """One pdfplumber drawing or image record's box as typed geometry.

    Raises PdfLayoutError naming the first missing or non-numeric edge.
    """
    values: list[float] = []
    for key in ("x0", "top", "x1", "bottom"):
        value = raw.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise PdfLayoutError(f"graphics record box has no numeric {key!r}")
        values.append(float(value))
    return (values[0], values[1], values[2], values[3])


def _visible(color: object) -> bool:
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


def page_graphics(
    page: Page,
    words: Sequence[PdfWord],
    tables: Sequence[tuple[float, float, float, float]],
    text_left: float,
) -> PageGraphics:
    """One page's pictures, vector paths, words, visual lines and text tables as boxes."""

    strokes: list[PdfStroke] = []
    kinds: tuple[tuple[Literal["line", "rect", "curve"], _Records], ...] = (
        ("line", page.lines),
        ("rect", page.rects),
        ("curve", page.curves),
    )
    for kind, objects in kinds:
        for raw in objects:
            strokes.append(
                PdfStroke(
                    box=_object_box(raw),
                    kind=kind,
                    stroked=bool(raw.get("stroke")) and _visible(raw.get("stroking_color")),
                    filled=bool(raw.get("fill")) and _visible(raw.get("non_stroking_color")),
                    evenodd=bool(raw.get("evenodd")),
                )
            )
    index = {id(word): position for position, word in enumerate(words)}
    return PageGraphics(
        width=float(page.width),
        height=float(page.height),
        images=tuple(_object_box(raw) for raw in page.images),
        strokes=tuple(strokes),
        words=tuple((word.x0, word.top, word.x1, word.bottom) for word in words),
        lines=tuple(tuple(index[id(word)] for word in line) for line in raw_lines(words)),
        tables=tuple(tables),
        text_left=text_left,
    )


def _font_marks(fontname: str) -> tuple[bool, bool]:
    name = _SUBSET_PREFIX.sub("", fontname)
    return _BOLD.search(name) is not None, _ITALIC.search(name) is not None


def read_words(page: Page) -> list[PdfWord]:
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


def float_box(raw: Sequence[float]) -> tuple[float, float, float, float]:
    return (float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3]))


def cell_count(table: Table) -> int:
    return sum(1 for row in table.rows for cell in row.cells if cell is not None)


def table_item(
    table: Table,
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
            bbox = float_box(cell)
            inside = [word for word in words if word_inside(word, bbox)]
            cells.append(
                tuple(
                    PdfLine(page_index, column, tuple(raw), bbox[0], bbox[2])
                    for raw in raw_lines(inside)
                )
            )
        rows.append(tuple(cells))
    return PdfTable(page=page_index, column=column, top=box[1], rows=tuple(rows))
