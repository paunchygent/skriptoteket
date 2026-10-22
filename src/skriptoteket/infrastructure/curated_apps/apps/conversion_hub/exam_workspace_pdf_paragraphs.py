"""Group a PDF's laid-out lines into paragraphs and render them (ST-SKRIPT-39-10 P5).

- Paragraphs: with paragraph spacing, lines one wrap pitch apart are one paragraph, joined
  with a space where Word wrapped and a newline where the teacher broke the line; a larger
  step ends the paragraph. Across a column or page break, or without paragraph spacing,
  only a wrap continues, and a closed sentence followed by a capital ends the paragraph.
  A change of font size or a printed answer line (underscores) always starts a new one,
  so the Word path's answer-line gate sees each answer line as its own chunk. A leading
  bullet glyph is dropped, as Word's list bullets are not paragraph text.
- Headings: a short paragraph clearly larger than the body text. The distinct heading
  sizes rank from the largest as levels 1-3, the way Title and Heading 1-3 nest in Word.

Bold and italic come from the font name, the only marks a PDF keeps reliably. Italic is
wrapped in ``<i>...</i>`` in ``marked_text`` exactly as the Word chunker does, because it
is the converter's cue for inline facit.

Relationships:
    ``exam_workspace_pdf_blocks`` groups and renders the body's paragraphs here, and
    ``exam_workspace_pdf_block_tables`` each table cell's; ``exam_workspace_pdf_items``
    holds the line types.
"""

from __future__ import annotations

import re
import statistics
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxSourceRun
from skriptoteket.domain.curated_apps.exam_workspace.source_answer_space import (
    is_answer_line_text,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_items import (  # noqa: E501
    WORD_SPACE_RATIO,
    PdfLine,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_pictures import (  # noqa: E501
    PdfBlockItem,
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
# A heading is at least this much larger than the body text and at most this long.
_HEADING_RATIO = 1.08
_HEADING_MAX_CHARS = 200
_POINTS_PER_INDENT_SPACE = 9.0


@dataclass(frozen=True)
class Spacing:
    """The document's wrapped-line pitch over font size, and whether its paragraphs are
    spaced apart; without paragraph spacing a line pitch cannot end a paragraph."""

    wrap_pitch: float
    spaced: bool


def line_spacing(items: Sequence[PdfBlockItem]) -> Spacing:
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
        return Spacing(wrap_pitch=_DEFAULT_WRAP_PITCH, spaced=True)
    wrap_pitch = statistics.quantiles(ratios, n=5)[0]
    spaced = sum(ratio > wrap_pitch * _PARAGRAPH_STEP for ratio in ratios) >= _SPACED_MIN_STEPS
    return Spacing(wrap_pitch=wrap_pitch, spaced=spaced)


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


def _line_break(previous: PdfLine, line: PdfLine, spacing: Spacing) -> str | None:
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
class Paragraph:
    """Lines of one paragraph; ``breaks[i]`` joins line ``i`` to line ``i + 1``."""

    lines: tuple[PdfLine, ...]
    breaks: tuple[str, ...] = ()


def paragraphs_of(lines: Sequence[PdfLine], spacing: Spacing) -> list[Paragraph]:
    grouped: list[Paragraph] = []
    for line in lines:
        joint = _line_break(grouped[-1].lines[-1], line, spacing) if grouped else None
        if joint is None:
            grouped.append(Paragraph(lines=(line,)))
        else:
            last = grouped[-1]
            grouped[-1] = Paragraph(lines=(*last.lines, line), breaks=(*last.breaks, joint))
    return grouped


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


def render(paragraph: Paragraph, *, left: float) -> _Rendered:
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


def heading_levels(paragraphs: Sequence[Paragraph], body_size: float) -> dict[int, int]:
    """Heading level per paragraph index: distinct larger sizes ranked from the largest."""
    candidates: dict[int, float] = {}
    for index, paragraph in enumerate(paragraphs):
        size = min(word.size for line in paragraph.lines for word in line.words)
        length = sum(len(line.text) for line in paragraph.lines)
        if size >= body_size * _HEADING_RATIO and length <= _HEADING_MAX_CHARS:
            candidates[index] = round(size)
    ranked = sorted(set(candidates.values()), reverse=True)
    return {index: min(3, ranked.index(size) + 1) for index, size in candidates.items()}
