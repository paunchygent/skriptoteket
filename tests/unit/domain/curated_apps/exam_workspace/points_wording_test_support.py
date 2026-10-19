"""Shared builders for the points-wording rule-family tests.

The shape, end-of-body, first-paragraph, heading and settlement tests build
the same paragraph and item shapes; the grouped checks read the item's body
either way.
"""

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeSegment,
    NativeTextMark,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
)


def text_segment(text: str, marks: tuple[NativeTextMark, ...] = ()) -> NativeTextSegment:
    return NativeTextSegment(text=text, marks=marks)


def paragraph(*segments: NativeSegment) -> NativeParagraph:
    return NativeParagraph(heading_level=None, segments=tuple(segments))


def heading(text: str, level: int = 3) -> NativeParagraph:
    return NativeParagraph(heading_level=level, segments=(text_segment(text),))


def heading2(text: str) -> NativeParagraph:
    return NativeParagraph(heading_level=2, segments=(text_segment(text),))


def item(body: tuple[NativeParagraph, ...], points: int | float | None) -> NativeExamItem:
    return make_free_text_item().model_copy(update={"body": body, "points": points})


VOLT = (
    "Pelle gör en fin volt, Sara gör en ful. Sätt poäng på Sara och Pelles volter. "
    "Använd mellan 3 poäng och 5 poäng."
)
