"""The one print layout owner for printed exams (TASK-SKRIPT-40-04-07 W6-W8).

Purpose:
    Decide, per native exam item, how its answer space prints. The student PDF, the
    facit PDF, the DOCX student copy and the Förhandsgranska preview all read this
    module instead of inventing their own answer forms, so the printed answer space
    is decided in exactly one place.

    W6 (the structural short-answer rule): a gap_fill question whose gap stands alone
    in its own paragraph prints as one full-width handwriting answer line. W7 (gap
    blank sizing): a gap inside a sentence prints as a handwriting blank sized for the
    longest accepted answer, and gap-fill paragraphs keep writing-height line spacing.
    W8 (choice answer forms): single and multiple choice options get tick boxes, while
    matching and ordering keep their own boxes.

Relationships:
    Reads the item's kind and body (``native_exam_item``, ``native_exam_body``), the
    declared gaps' accepted values (``native_exam_values``) and the house template's
    measures (``exam_conversion.exam_print_house_template``). It is a leaf reader: no
    renderer writes back into it.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    TEXT_WIDTH_MM,
    blank_width_mm,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)


class ParagraphPrintRole(StrEnum):
    """How one body paragraph prints its answer space.

    ``TEXT`` is ordinary prose with no gap. ``GAP_LINE`` holds at least one gap inside a
    sentence, so its blanks are writable on a writing-height line (W7). ``ANSWER_LINE`` is
    a paragraph whose only content is a gap, printed as one full-width handwriting line
    (W6).
    """

    TEXT = "text"
    GAP_LINE = "gap_line"
    ANSWER_LINE = "answer_line"


@dataclass(frozen=True)
class GapPrintForm:
    """The printed form of one gap: a standalone answer line or a sized inline blank."""

    gap_id: str
    answer_line: bool
    width_mm: float


@dataclass(frozen=True)
class ItemPrintLayout:
    """The answer space one item prints: ruled writing lines, gap forms and tick boxes."""

    writing_lines: int
    gap_forms: Mapping[str, GapPrintForm]
    tick_boxes: bool


def is_answer_line_paragraph(paragraph: NativeParagraph) -> bool:
    """Whether a paragraph is a standalone gap printed as one handwriting line (W6).

    Only structure decides this, never the wording: the paragraph's whitespace-only text
    runs are ignored and its remaining segments must be exactly one gap.
    """

    significant = [
        segment
        for segment in paragraph.segments
        if not (isinstance(segment, NativeTextSegment) and segment.text.strip() == "")
    ]
    return len(significant) == 1 and isinstance(significant[0], NativeGapSegment)


def paragraph_print_role(item: NativeExamItem, paragraph: NativeParagraph) -> ParagraphPrintRole:
    """The print role of one body paragraph of ``item`` (W6, W7)."""
    if item.kind is not NativeExamItemKind.GAP_FILL:
        return ParagraphPrintRole.TEXT
    if is_answer_line_paragraph(paragraph):
        return ParagraphPrintRole.ANSWER_LINE
    if any(isinstance(segment, NativeGapSegment) for segment in paragraph.segments):
        return ParagraphPrintRole.GAP_LINE
    return ParagraphPrintRole.TEXT


def item_print_layout(item: NativeExamItem) -> ItemPrintLayout:
    """The complete print layout of one native exam item (W6, W7, W8)."""
    kind = item.kind
    writing_lines = 0
    if kind is NativeExamItemKind.FREE_TEXT:
        # The model guarantees a free-text question always carries its line count.
        assert item.writing_lines is not None
        writing_lines = item.writing_lines

    tick_boxes = kind in (
        NativeExamItemKind.SINGLE_CHOICE,
        NativeExamItemKind.MULTIPLE_RESPONSE,
    )

    gap_forms: dict[str, GapPrintForm] = {}
    if kind is NativeExamItemKind.GAP_FILL:
        accepted_values = {gap.gap_id: gap.accepted_values for gap in item.gaps}
        for paragraph in item.body:
            answer_line = paragraph_print_role(item, paragraph) is ParagraphPrintRole.ANSWER_LINE
            for segment in paragraph.segments:
                if not isinstance(segment, NativeGapSegment):
                    continue
                gap_forms[segment.gap_id] = GapPrintForm(
                    gap_id=segment.gap_id,
                    answer_line=answer_line,
                    width_mm=_gap_form_width_mm(
                        accepted_values[segment.gap_id], answer_line=answer_line
                    ),
                )

    return ItemPrintLayout(
        writing_lines=writing_lines,
        gap_forms=MappingProxyType(gap_forms),
        tick_boxes=tick_boxes,
    )


def _gap_form_width_mm(accepted_values: tuple[str, ...], *, answer_line: bool) -> float:
    """The printed width of one gap: full width on an answer line, else the sized blank (W6, W7).

    An inline_choice gap never reaches here: it prints its own option list instead (W8).
    """
    if answer_line:
        return TEXT_WIDTH_MM
    longest = max((len(value.strip()) for value in accepted_values), default=0)
    return blank_width_mm(longest)
