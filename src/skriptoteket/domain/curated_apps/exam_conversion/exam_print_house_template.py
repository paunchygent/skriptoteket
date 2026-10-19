"""One fixed handwriting-first house template for every printed exam surface (W1, W3).

The student PDF, the facit PDF, the DOCX student copy and the preview share this
single template: one readable font, generous line spacing, writing lines spaced for
a hand, and every block and answer-form dimension below. The 2026-10-18 ruling makes
this module the one layout owner for the DOCX and the print PDF/preview, so both
renderers read these measures instead of inventing their own. There are deliberately
no template settings.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType


class ExamPrintVariant(StrEnum):
    STUDENT = "student"  # writing areas and answer forms, no answers
    FACIT = "facit"  # the same pages with each question's answer key and criteria after it


DEFAULT_WRITING_LINES = 8
MIN_WRITING_LINES = 1
MAX_WRITING_LINES = 40

HOUSE_FONT_FAMILIES: tuple[str, ...] = ("Liberation Sans", "DejaVu Sans")
HOUSE_FONT_SIZE_PT = 12
HOUSE_LINE_HEIGHT = 1.5
WRITING_LINE_PITCH_MM = 10.0

PAGE_WIDTH_MM = 210.0
PAGE_HEIGHT_MM = 297.0  # A4 page height; with PAGE_WIDTH_MM = 210.0 both pages are A4.
PAGE_MARGIN_VERTICAL_MM = 18.0
PAGE_MARGIN_SIDE_MM = 18.0
TEXT_WIDTH_MM = PAGE_WIDTH_MM - 2 * PAGE_MARGIN_SIDE_MM

TEXT_COLOR_HEX = "111111"  # body and heading text, box borders, grid cell borders.
RULE_COLOR_HEX = "555555"  # ruled writing lines and the gap blank underline.


@dataclass(frozen=True)
class BlockSpacing:
    """One printed block's space before and after, in millimetres."""

    space_before_mm: float
    space_after_mm: float


@dataclass(frozen=True)
class HeadingGeometry:
    """One heading level's print geometry: font size and block spacing."""

    size_pt: float
    spacing: BlockSpacing


# One entry per heading level the print document emits; every heading is bold, in
# TEXT_COLOR_HEX, in the house font and kept with the next block.
HEADING_GEOMETRY: Mapping[int, HeadingGeometry] = MappingProxyType(
    {
        1: HeadingGeometry(18, BlockSpacing(0, 6)),  # the exam title.
        3: HeadingGeometry(14, BlockSpacing(0, 3)),  # one question's title.
    }
)

PARAGRAPH_SPACING = BlockSpacing(0, 2)  # an ordinary body paragraph.
QUESTION_SPACE_AFTER_MM = 8.0  # space after a whole question block.
INSTRUCTION_SPACE_AFTER_MM = 6.0  # space after a whole shared instruction block.
OPTION_SPACING = BlockSpacing(0, 3)  # one answer option paragraph.
WRITING_AREA_SPACING = BlockSpacing(2, 4)  # before the first ruled line, after the last.
GRID_SPACING = BlockSpacing(2, 4)  # before and after a matching grid.
RULE_WEIGHT_PT = 0.5  # ruled writing lines and the gap blank underline.
TICK_BOX_GLYPH = "☐"  # the ballot box every tick box and grid cell prints.
NUMBER_BOX_WIDTH_MM = 9.0  # one empty number box's width; it is one text line high.
BOX_GAP_MM = 2.0  # space between a box and its option text.
BOX_BORDER_PT = 1.0  # the number box border weight.
# One house-font 12 pt non-breaking space; DOCX blanks and number boxes fill with it.
NBSP_WIDTH_MM = 1.18
GRID_CELL_PADDING_MM = 2.0  # one matching grid cell's padding.
IMAGE_SPACING = BlockSpacing(2, 2)  # before and after a printed picture.
ANSWER_KEY_RULE_PT = 2.0  # the facit answer key's left rule weight.
ANSWER_KEY_INDENT_MM = 3.0  # the facit answer key's left indent.
ANSWER_KEY_SPACING = BlockSpacing(2, 4)  # before and after a facit answer key.

BLANK_MM_PER_CHARACTER = 4.0
BLANK_PADDING_MM = 8.0
BLANK_MIN_WIDTH_MM = 30.0


def blank_width_mm(longest_answer_characters: int) -> float:
    """Handwriting blank for a gap inside a sentence: room for the longest accepted answer (W7)."""
    width = longest_answer_characters * BLANK_MM_PER_CHARACTER + BLANK_PADDING_MM
    return min(TEXT_WIDTH_MM, max(BLANK_MIN_WIDTH_MM, width))
