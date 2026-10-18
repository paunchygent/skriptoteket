"""One fixed handwriting-first house template for every printed exam surface (W3).

The student PDF, the facit PDF, the DOCX student copy and the preview share this
single template: one readable font, generous line spacing and writing lines
spaced for a hand. There are deliberately no template settings; callers read
these measures instead of inventing their own.
"""

from __future__ import annotations

from enum import StrEnum


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
PAGE_MARGIN_VERTICAL_MM = 18.0
PAGE_MARGIN_SIDE_MM = 18.0
TEXT_WIDTH_MM = PAGE_WIDTH_MM - 2 * PAGE_MARGIN_SIDE_MM

BLANK_MM_PER_CHARACTER = 4.0
BLANK_PADDING_MM = 8.0
BLANK_MIN_WIDTH_MM = 30.0


def blank_width_mm(longest_answer_characters: int) -> float:
    """Handwriting blank for a gap inside a sentence: room for the longest accepted answer (W7)."""
    width = longest_answer_characters * BLANK_MM_PER_CHARACTER + BLANK_PADDING_MM
    return min(TEXT_WIDTH_MM, max(BLANK_MIN_WIDTH_MM, width))
