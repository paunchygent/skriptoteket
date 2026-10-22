"""Find tables Word drew without borders and render table chunks (ST-SKRIPT-39-10 P5).

- Tables: a ruled table, or two or more rows whose cells start at the same places (a
  table Word drew without borders), become one table chunk, cells joined with `` | `` and
  rows with a newline like the Word chunker; a cell's paragraphs join with a newline.

Relationships:
    ``exam_workspace_pdf_blocks`` finds the borderless tables and renders every table
    here; ``exam_workspace_pdf_paragraphs`` groups and renders each cell's paragraphs.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxSourceParagraph,
    DocxSourceRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import POINT_LABEL
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_items import (  # noqa: E501
    PdfLine,
    PdfTable,
    PdfWord,
    joined_words,
    raw_lines,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_paragraphs import (  # noqa: E501
    Spacing,
    paragraphs_of,
    render,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_pictures import (  # noqa: E501
    PdfBlockItem,
)

# Borderless tables: a cell starts after a gap at least this wide (or a font size) on the
# row that finds the table, after more than half a font size on the other rows; starts
# align within this many points; a wrapped cell line steps down at most this many wrap
# pitches.
_CELL_MIN_POINTS = 12.0
_CELL_GAP_RATIO = 1.0
_CELL_MIN_GAP_RATIO = 0.5
_CELL_ALIGN_POINTS = 3.0
_ROW_STEP = 1.15


def _cell_starts(line: PdfLine) -> list[float]:
    """Where each cell after the first begins: a word after a gap wider than a font size.

    Points tabbed to the right margin, such as "(2p)", end the line's text; they start
    no cell.
    """
    return [
        word.x0
        for index, (previous, word) in enumerate(zip(line.words, line.words[1:], strict=False))
        if word.x0 - previous.x1 >= max(_CELL_MIN_POINTS, word.size * _CELL_GAP_RATIO)
        and POINT_LABEL.fullmatch(joined_words(line.words[index + 1 :])) is None
    ]


def _aligned(start: float, columns: Sequence[float]) -> bool:
    return any(abs(start - column) <= _CELL_ALIGN_POINTS for column in columns)


def _is_row(line: PdfLine, columns: Sequence[float]) -> bool:
    """A new row: a word starts each of the table's cells after more than a space, and no
    other cell-wide gap opens. A short cell may leave less than a cell-wide gap."""
    if any(not _aligned(start, columns) for start in _cell_starts(line)):
        return False
    cell_starts = [
        word.x0
        for previous, word in zip(line.words, line.words[1:], strict=False)
        if word.x0 - previous.x1 >= word.size * _CELL_MIN_GAP_RATIO
    ]
    return all(
        any(abs(start - column) <= _CELL_ALIGN_POINTS for start in cell_starts)
        for column in columns
    )


def _cell_bound(line: PdfLine, columns: Sequence[float]) -> float:
    """The right end of the cell a line starts in: the next cell's start."""
    following = [start for start in columns if start > line.x0 + _CELL_ALIGN_POINTS]
    return following[0] - _CELL_ALIGN_POINTS if following else line.right_edge


def _continues_row(
    previous: PdfLine, line: PdfLine, columns: Sequence[float], spacing: Spacing
) -> bool:
    """Wrapped cell text of the row above: one wrap pitch down, inside the table's cells."""
    if (line.page, line.column) != (previous.page, previous.column):
        return False
    if line.top - previous.top > spacing.wrap_pitch * line.size * _ROW_STEP:
        return False
    starts = _cell_starts(line)
    if starts:
        return all(_aligned(start, columns) for start in starts)
    return line.x1 <= _cell_bound(line, columns)


def _column_of(word: PdfWord, columns: Sequence[float]) -> int:
    return sum(1 for start in columns if word.x0 >= start - _CELL_ALIGN_POINTS)


def _table_rows(
    lines: Sequence[PdfLine], columns: Sequence[float]
) -> tuple[tuple[tuple[PdfLine, ...], ...], ...]:
    """A borderless table's lines as rows of cells, each cell its own lines."""
    lefts = [lines[0].left_edge, *columns]
    rows: list[list[list[PdfWord]]] = []
    for line in lines:
        if not rows or _is_row(line, columns):
            rows.append([[] for _ in lefts])
        for word in line.words:
            rows[-1][_column_of(word, columns)].append(word)
    # A cell's text ends where its column's widest line ends, not at the next cell's start.
    rights = [
        max((word.x1 for row in rows for word in row[i]), default=lefts[i])
        for i in range(len(lefts))
    ]
    return tuple(
        tuple(
            tuple(
                PdfLine(lines[0].page, lines[0].column, tuple(raw), lefts[i], rights[i])
                for raw in raw_lines(cell)
            )
            for i, cell in enumerate(row)
        )
        for row in rows
    )


def _borderless_tables(lines: Sequence[PdfLine], spacing: Spacing) -> list[PdfLine | PdfTable]:
    """Runs of rows whose cells start at the same places become tables.

    Word draws a table without borders as words alone, yet its cells begin at the same x
    on every row. Two or more such rows in one column, with the wrapped cell lines between
    and after them, are one table; every other line passes through.
    """
    result: list[PdfLine | PdfTable] = []
    index = 0
    while index < len(lines):
        first = lines[index]
        columns = _cell_starts(first)
        rows, end = 1, index + 1
        while columns and end < len(lines):
            line = lines[end]
            if _is_row(line, columns) and (line.page, line.column) == (first.page, first.column):
                rows += 1
            elif not _continues_row(lines[end - 1], line, columns, spacing):
                break
            end += 1
        if rows < 2:
            result.append(first)
            index += 1
            continue
        # Rows above whose short cells left a narrower gap still start at the cell starts.
        while (
            result
            and isinstance(result[-1], PdfLine)
            and (result[-1].page, result[-1].column) == (first.page, first.column)
            and _is_row(result[-1], columns)
        ):
            result.pop()
            index -= 1
        first = lines[index]
        run = lines[index:end]
        result.append(
            PdfTable(
                page=first.page, column=first.column, top=first.top, rows=_table_rows(run, columns)
            )
        )
        index = end
    return result


def table_block(
    table: PdfTable, spacing: Spacing
) -> tuple[str, str, str, list[DocxSourceParagraph], list[DocxSourceRun]]:
    """A table's text, marked text, GFM markdown and source formatting, like the Word chunker."""
    plain: list[str] = []
    marked: list[str] = []
    markdown_rows: list[str] = []
    paragraphs: list[DocxSourceParagraph] = []
    runs: list[DocxSourceRun] = []
    offset = 0

    def add(text: str, marked_text: str) -> None:
        nonlocal offset
        plain.append(text)
        marked.append(marked_text)
        offset += len(text)

    for row_index, row in enumerate(table.rows):
        if row_index:
            add("\n", "\n")
        cells_markdown: list[str] = []
        for cell_index, cell in enumerate(row):
            if cell_index:
                add(" | ", " | ")
            left = min((line.x0 for line in cell), default=0.0)
            cell_markdown: list[str] = []
            for paragraph_index, paragraph in enumerate(paragraphs_of(cell, spacing)):
                if paragraph_index:
                    add("\n", "\n")
                rendered = render(paragraph, left=left)
                paragraphs.append(DocxSourceParagraph(offset=offset, text=rendered.text))
                runs.extend(replace(run, offset=offset + run.offset) for run in rendered.runs)
                add(rendered.text, rendered.marked)
                cell_markdown.append(rendered.markdown.strip())
            cells_markdown.append("<br>".join(cell_markdown))
        markdown_rows.append("| " + " | ".join(cells_markdown) + " |")
    if markdown_rows:
        width = max(len(row) for row in table.rows)
        markdown_rows.insert(1, "| " + " | ".join("---" for _ in range(width)) + " |")
    return "".join(plain), "".join(marked), "\n".join(markdown_rows), paragraphs, runs


def with_borderless_tables(items: Sequence[PdfBlockItem], spacing: Spacing) -> list[PdfBlockItem]:
    """Each run of lines between ruled tables and pictures, with its borderless tables found."""
    result: list[PdfBlockItem] = []
    run: list[PdfLine] = []
    for item in [*items, None]:
        if isinstance(item, PdfLine):
            run.append(item)
            continue
        result.extend(_borderless_tables(run, spacing))
        run = []
        if item is not None:
            result.append(item)
    return result
