"""Rebuild the Word import's chunks from one PDF's laid-out lines (ST-SKRIPT-39-10 P5).

The blocks are the ones the Word chunker produces, so the existing Word conversion path
runs on them unchanged:

- Paragraphs: with paragraph spacing, lines one wrap pitch apart are one paragraph, joined
  with a space where Word wrapped and a newline where the teacher broke the line; a larger
  step ends the paragraph. Across a column or page break, or without paragraph spacing,
  only a wrap continues, and a closed sentence followed by a capital ends the paragraph.
  A change of font size or a printed answer line (underscores) always starts a new one,
  so the Word path's answer-line gate sees each answer line as its own chunk. A leading
  bullet glyph is dropped, as Word's list bullets are not paragraph text.
- Headings: a short paragraph clearly larger than the body text. The distinct heading
  sizes rank from the largest as levels 1-3, the way Title and Heading 1-3 nest in Word.
- Tables: a ruled table, or two or more rows whose cells start at the same places (a
  table Word drew without borders), become one table chunk, cells joined with `` | `` and
  rows with a newline like the Word chunker; a cell's paragraphs join with a newline.
- Pictures: a cut picture or figure is a chunk of its own, ``kind="drawing"`` with empty
  text and the picture, as the Word chunker gives a paragraph holding only a picture.

Bold and italic come from the font name, the only marks a PDF keeps reliably. Italic is
wrapped in ``<i>...</i>`` in ``marked_text`` exactly as the Word chunker does, because it
is the converter's cue for inline facit. Each block also carries its labeler markdown in
the Word labeler's form: ``#`` headings, ``**bold**``, ``- `` bullets and GFM tables.
"""

from __future__ import annotations

import re
import statistics
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxImage,
    DocxSourceParagraph,
    DocxSourceRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import POINT_LABEL
from skriptoteket.domain.curated_apps.exam_workspace.source_answer_space import (
    is_answer_line_text,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_layout import (  # noqa: E501
    WORD_SPACE_RATIO,
    PdfLine,
    PdfTable,
    PdfWord,
    joined_words,
    raw_lines,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_pictures import (  # noqa: E501
    PdfBlockItem,
    PdfPicture,
)

_BULLET_CHARACTERS = (
    "\u2022\u25e6\u25aa\u25ab\u25a0\u25a1\u25cf\u25cb\u2023\u2043\u2219\u00b7\uf0b7\uf0a7\uf0d8"
)
_BULLETS = frozenset(_BULLET_CHARACTERS)
_LIST_MARKER = re.compile(rf"^(?:[{_BULLET_CHARACTERS}]|\(?[0-9]{{1,2}}[.)]|\(?[a-zA-Z][.)])$")

# A wrapped line's pitch over font size; a step larger than this many of the document's
# own wrap pitches is paragraph spacing, and a document shows spacing when at least this
# many steps are that large.
_DEFAULT_WRAP_PITCH = 1.35
_PARAGRAPH_STEP = 1.25
_SPACED_MIN_STEPS = 3
_SENTENCE_END = frozenset(".?!:)")
_SIZE_CHANGE_POINTS = 0.6
# The width of a space over font size, and a paragraph's last line: it leaves more than
# this share of its column empty.
_SPACE_WIDTH = 0.3
_WRAP_MAX_SLACK = 0.25
# Borderless tables: a cell starts after a gap at least this wide (or a font size) on the
# row that finds the table, after more than half a font size on the other rows; starts
# align within this many points; a wrapped cell line steps down at most this many wrap
# pitches.
_CELL_MIN_POINTS = 12.0
_CELL_GAP_RATIO = 1.0
_CELL_MIN_GAP_RATIO = 0.5
_CELL_ALIGN_POINTS = 3.0
_ROW_STEP = 1.15
# A heading is at least this much larger than the body text and at most this long.
_HEADING_RATIO = 1.08
_HEADING_MAX_CHARS = 200
_POINTS_PER_INDENT_SPACE = 9.0
_FALLBACK_BODY_POINTS = 11.0


@dataclass(frozen=True)
class PdfBlock:
    """One rebuilt block: the Word-shaped chunk and its labeler markdown (D14)."""

    chunk: DocxChunk
    markdown: str


@dataclass(frozen=True)
class _Spacing:
    """The document's wrapped-line pitch over font size, and whether its paragraphs are
    spaced apart; without paragraph spacing a line pitch cannot end a paragraph."""

    wrap_pitch: float
    spaced: bool


def _spacing(items: Sequence[PdfBlockItem]) -> _Spacing:
    """The low end of line steps is the wrap pitch; larger steps show paragraph spacing.

    Only lines next to each other in the reading order count: the step across a table
    or a picture between them is that item's height, not paragraph spacing.
    """
    ratios: list[float] = []
    for previous, line in zip(items, items[1:], strict=False):
        if not isinstance(previous, PdfLine) or not isinstance(line, PdfLine):
            continue
        if (line.page, line.column) == (previous.page, previous.column) and abs(
            line.size - previous.size
        ) <= _SIZE_CHANGE_POINTS:
            step = line.top - previous.top
            if step > 0:
                ratios.append(step / line.size)
    if len(ratios) < 4:
        return _Spacing(wrap_pitch=_DEFAULT_WRAP_PITCH, spaced=True)
    wrap_pitch = statistics.quantiles(ratios, n=5)[0]
    spaced = sum(ratio > wrap_pitch * _PARAGRAPH_STEP for ratio in ratios) >= _SPACED_MIN_STEPS
    return _Spacing(wrap_pitch=wrap_pitch, spaced=spaced)


def _ends_sentence(previous: PdfLine, line: PdfLine) -> bool:
    """The previous line closes a sentence or a points mark and the next opens one."""
    first = line.words[0].text[:1]
    return previous.words[-1].text[-1:] in _SENTENCE_END and (first.isupper() or first.isdigit())


def _is_answer_line(line: PdfLine) -> bool:
    return is_answer_line_text(line.text)


def _starts_list(line: PdfLine) -> bool:
    return _LIST_MARKER.fullmatch(line.words[0].text) is not None


def _wrapped_onto(previous: PdfLine, line: PdfLine) -> bool:
    """True when ``line`` holds words Word wrapped off ``previous`` for lack of room."""
    first = line.words[0]
    slack = previous.right_edge - previous.x1
    if slack >= first.size * _SPACE_WIDTH + (first.x1 - first.x0):
        return False  # Word would have placed the next word on the previous line.
    # A wrapped line seldom leaves this much of its column empty.
    return slack <= (previous.right_edge - previous.left_edge) * _WRAP_MAX_SLACK


def _line_break(previous: PdfLine, line: PdfLine, spacing: _Spacing) -> str | None:
    """How ``line`` joins ``previous``'s paragraph: ``" "`` after a wrap, ``"\\n"`` after a
    line break inside the paragraph, or None when ``line`` starts a new paragraph."""
    if abs(line.size - previous.size) > _SIZE_CHANGE_POINTS:
        return None
    if _is_answer_line(previous) or _is_answer_line(line):
        return None
    if line.words[0].text in _BULLETS:
        return None  # Every bullet is its own list paragraph, however close the lines sit.
    wrapped = _wrapped_onto(previous, line)
    same_column = (line.page, line.column) == (previous.page, previous.column)
    if same_column and spacing.spaced:
        # Paragraph spacing is the paragraph boundary; a line that steps by the wrap pitch
        # without being wrapped follows a line break (Shift+Enter) in the same paragraph.
        if line.top - previous.top > spacing.wrap_pitch * line.size * _PARAGRAPH_STEP:
            return None
        return " " if wrapped else "\n"
    # Across a column or page break, or with unspaced paragraphs, only a wrap continues,
    # and a closed sentence followed by a capital ends the paragraph: two questions merged
    # into one chunk cannot be told apart later, a paragraph split in two still groups.
    if not wrapped or _starts_list(line) or _ends_sentence(previous, line):
        return None
    return " "


@dataclass(frozen=True)
class _Paragraph:
    """Lines of one paragraph; ``breaks[i]`` joins line ``i`` to line ``i + 1``."""

    lines: tuple[PdfLine, ...]
    breaks: tuple[str, ...] = ()


def _paragraphs(lines: Sequence[PdfLine], spacing: _Spacing) -> list[_Paragraph]:
    grouped: list[_Paragraph] = []
    for line in lines:
        joint = _line_break(grouped[-1].lines[-1], line, spacing) if grouped else None
        if joint is None:
            grouped.append(_Paragraph(lines=(line,)))
        else:
            last = grouped[-1]
            grouped[-1] = _Paragraph(lines=(*last.lines, line), breaks=(*last.breaks, joint))
    return grouped


# --- Borderless tables --------------------------------------------------------------------


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
    previous: PdfLine, line: PdfLine, columns: Sequence[float], spacing: _Spacing
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


def _borderless_tables(lines: Sequence[PdfLine], spacing: _Spacing) -> list[PdfLine | PdfTable]:
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


@dataclass(frozen=True)
class _Rendered:
    text: str
    marked: str
    markdown: str
    runs: tuple[DocxSourceRun, ...]


def _stretches(
    pieces: Sequence[tuple[str, bool, bool]],
    *,
    key: Callable[[bool, bool], tuple[bool, ...]],
) -> list[tuple[tuple[bool, ...], str]]:
    """Adjacent text pieces joined while ``key`` of their marks stays the same."""
    stretches: list[tuple[tuple[bool, ...], str]] = []
    for text, bold, italic in pieces:
        marks = key(bold, italic)
        if stretches and stretches[-1][0] == marks:
            stretches[-1] = (marks, stretches[-1][1] + text)
        else:
            stretches.append((marks, text))
    return stretches


def _wrapped(text: str, template: str) -> str:
    """``text`` with its stripped core put into ``template``; surrounding space stays outside."""
    core = text.strip()
    if not core:
        return text
    start = text.index(core)
    return text[:start] + template.format(core) + text[start + len(core) :]


def _render(paragraph: _Paragraph, *, left: float) -> _Rendered:
    """One paragraph's plain text, italic-marked text, labeler markdown and source runs."""
    lines = paragraph.lines
    pieces: list[tuple[str, bool, bool]] = []
    for line_index, line in enumerate(lines):
        words = list(line.words)
        if line_index == 0 and words and words[0].text in _BULLETS:
            words = words[1:]
        for index, word in enumerate(words):
            gap = ""
            if index == 0 and line_index and pieces:
                gap = paragraph.breaks[line_index - 1]
                if gap == "\n":
                    # A line break carries no marks, so marked stretches end at it as in Word.
                    pieces.append((gap, False, False))
                    gap = ""
            elif index and word.x0 - words[index - 1].x1 > word.size * WORD_SPACE_RATIO:
                gap = " "
            pieces.append((gap + word.text, word.bold, word.italic))
    stretches = _stretches(pieces, key=lambda bold, italic: (bold, italic))
    plain = "".join(text for _, text in stretches)
    runs: list[DocxSourceRun] = []
    markdown_parts: list[str] = []
    offset = 0
    for (bold, italic), text in stretches:
        marks = tuple(mark for mark, on in (("bold", bold), ("italic", italic)) if on)
        runs.append(DocxSourceRun(offset=offset, text=text, marks=marks))
        offset += len(text)
        styled = "<i>{}</i>" if italic else "{}"
        markdown_parts.append(_wrapped(text, f"**{styled}**" if bold else styled))
    # Italic alone shapes the model's marked text, exactly like the Word chunker.
    marked = "".join(
        _wrapped(text, "<i>{}</i>" if italic else "{}")
        for (italic,), text in _stretches(pieces, key=lambda _bold, italic: (italic,))
    )
    bullet = lines[0].words[0].text in _BULLETS
    indent = max(0, round((lines[0].x0 - left) / _POINTS_PER_INDENT_SPACE))
    markdown = " " * indent + ("- " if bullet else "") + "".join(markdown_parts)
    return _Rendered(plain, marked, markdown, tuple(runs))


def _body_points(items: Sequence[PdfBlockItem]) -> float:
    sizes: Counter[float] = Counter()
    for item in items:
        if isinstance(item, PdfLine):
            for word in item.words:
                sizes[round(word.size, 1)] += len(word.text)
    return sizes.most_common(1)[0][0] if sizes else _FALLBACK_BODY_POINTS


def _heading_levels(paragraphs: Sequence[_Paragraph], body_points: float) -> dict[int, int]:
    """Heading level per paragraph index: distinct larger sizes ranked from the largest."""
    candidates: dict[int, float] = {}
    for index, paragraph in enumerate(paragraphs):
        size = min(word.size for line in paragraph.lines for word in line.words)
        length = sum(len(line.text) for line in paragraph.lines)
        if size >= body_points * _HEADING_RATIO and length <= _HEADING_MAX_CHARS:
            candidates[index] = round(size)
    ranked = sorted(set(candidates.values()), reverse=True)
    return {index: min(3, ranked.index(size) + 1) for index, size in candidates.items()}


def _table_block(
    table: PdfTable, spacing: _Spacing
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
            for paragraph_index, paragraph in enumerate(_paragraphs(cell, spacing)):
                if paragraph_index:
                    add("\n", "\n")
                rendered = _render(paragraph, left=left)
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


def _with_borderless_tables(items: Sequence[PdfBlockItem], spacing: _Spacing) -> list[PdfBlockItem]:
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


def pdf_blocks(items: Sequence[PdfBlockItem]) -> tuple[PdfBlock, ...]:
    """Every block in reading order, anchored ``body:0001`` onward like the Word chunker."""
    spacing = _spacing(items)
    body_points = _body_points(items)
    left = min((item.x0 for item in items if isinstance(item, PdfLine)), default=0.0)
    # Consecutive lines group into paragraphs; a table or a picture always stands alone.
    sequence: list[_Paragraph | PdfTable | PdfPicture] = []
    pending: list[PdfLine] = []
    for item in [*_with_borderless_tables(items, spacing), None]:
        if isinstance(item, PdfLine):
            pending.append(item)
            continue
        sequence.extend(_paragraphs(pending, spacing))
        pending = []
        if item is not None:
            sequence.append(item)
    levels = _heading_levels(
        [entry for entry in sequence if isinstance(entry, _Paragraph)], body_points
    )
    blocks: list[PdfBlock] = []
    paragraph_index = -1
    for entry in sequence:
        anchor = f"body:{len(blocks) + 1:04d}"
        if isinstance(entry, PdfPicture):
            picture = entry.picture
            chunk = DocxChunk(
                anchor=anchor,
                kind="drawing",
                text="",
                marked_text="",
                images=(picture,) if isinstance(picture, DocxImage) else (),
                missing_images=() if isinstance(picture, DocxImage) else (picture,),
                paragraphs=(DocxSourceParagraph(offset=0, text=""),),
            )
            blocks.append(PdfBlock(chunk=chunk, markdown=""))
            continue
        if isinstance(entry, PdfTable):
            text, marked, markdown, paragraphs, runs = _table_block(entry, spacing)
            if not text.replace("|", "").strip():
                continue
            chunk = DocxChunk(
                anchor=anchor,
                kind="table",
                text=text,
                marked_text=marked,
                runs=tuple(runs),
                paragraphs=tuple(paragraphs),
            )
            blocks.append(PdfBlock(chunk=chunk, markdown=markdown))
            continue
        paragraph_index += 1
        rendered = _render(entry, left=left)
        if not rendered.text.strip():
            continue
        level = levels.get(paragraph_index)
        chunk = DocxChunk(
            anchor=anchor,
            kind="heading" if level is not None else "paragraph",
            text=rendered.text,
            marked_text=rendered.marked,
            runs=rendered.runs,
            paragraphs=(DocxSourceParagraph(offset=0, text=rendered.text, heading_level=level),),
        )
        markdown = rendered.markdown
        if level is not None:
            markdown = "#" * level + " " + markdown.lstrip()
        blocks.append(PdfBlock(chunk=chunk, markdown=markdown))
    return tuple(blocks)
