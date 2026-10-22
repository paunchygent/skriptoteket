"""The laid-out items of one text PDF and the word helpers they share (ST-SKRIPT-39-10).

A PDF's words, each with its box, font size and bold or italic font, group into visual
lines by vertical overlap; a line reads its words left to right, with a space wherever
the gap is wider than a word space. The laid-out document is a sequence of lines, tables
and picture regions, each in one column or across the page.

Relationships:
    ``exam_workspace_pdf_page_adapter`` reads pdfplumber objects into these types;
    ``exam_workspace_pdf_furniture`` drops page furniture among them;
    ``exam_workspace_pdf_layout`` orders them; ``exam_workspace_pdf_pictures`` and
    ``exam_workspace_pdf_blocks`` turn them into Word-shaped chunks.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

# Word space: a gap between two words on one line wider than this share of the font size.
WORD_SPACE_RATIO = 0.15
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

    The box is in the page's word coordinates, clipped to ``visible``: the page's
    CropBox in them, the box PDFium renders. The rendered page's pixel grid starts
    at ``visible``'s top-left corner. ``mapped`` is False on a rotated page, whose
    coordinates share no pixel mapping; such a region is never cut. ``erase`` holds
    the boxes of every word on the page that overlaps the region's box and is not
    one of this cut's labels: the cutter paints them white, so answer text never
    reaches the picture's pixels.
    """

    page: int
    column: int
    kind: Literal["picture", "figure"]
    x0: float
    top: float
    x1: float
    bottom: float
    visible: tuple[float, float, float, float]
    mapped: bool
    erase: tuple[tuple[float, float, float, float], ...] = ()


PdfItem = PdfLine | PdfTable | PdfPictureRegion


def joined_words(words: Sequence[PdfWord]) -> str:
    """One line's words with a space wherever the gap is wider than a word space."""
    parts: list[str] = []
    for index, word in enumerate(words):
        if index and word.x0 - words[index - 1].x1 > word.size * WORD_SPACE_RATIO:
            parts.append(" ")
        parts.append(word.text)
    return "".join(parts)


def body_points(words: Iterable[PdfWord]) -> float:
    """The document's body font size: the most common word size, counted by characters."""
    sizes: Counter[float] = Counter()
    for word in words:
        sizes[round(word.size, 1)] += len(word.text)
    return sizes.most_common(1)[0][0] if sizes else _FALLBACK_BODY_POINTS


def word_inside(word: PdfWord, bbox: tuple[float, float, float, float]) -> bool:
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


def item_top(item: PdfItem) -> float:
    return item.top


def item_bottom(item: PdfItem) -> float:
    if isinstance(item, PdfLine | PdfPictureRegion):
        return item.bottom
    cells = [line.bottom for row in item.rows for cell in row for line in cell]
    return max(cells, default=item.top)
