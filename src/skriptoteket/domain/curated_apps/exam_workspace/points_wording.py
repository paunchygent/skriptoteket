"""Trailing points wording at the end of a native exam item body.

Printed points wording ("(1 point)", "Poäng: 6 poäng") states the item's
points, never its text: ``trailing_points`` finds such wording at the end of
a text, and ``body_without_trailing_points`` drops it from the last paragraph
when its number equals the item's points. Only the label's position and its
number decide; the stem itself is never read or rewritten.
"""

from __future__ import annotations

from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    POINT_LABEL,
    label_points,
    points_line,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem


@dataclass(frozen=True)
class TrailingPoints:
    """Points wording at the end of a text: where it starts and its number."""

    start: int
    value: int | float


def trailing_points(text: str) -> TrailingPoints | None:
    """Points wording at the end of a text, or None when the end holds prose.

    Two shapes count: a last line that is only a points line, which leaves
    with its newline, and a parenthesised label ending the last line, which
    leaves with the blank space before it. A label with no number is ignored.
    """
    stripped = text.rstrip()
    line_start = stripped.rfind("\n") + 1
    line = stripped[line_start:]
    matches = list(POINT_LABEL.finditer(line))
    if not matches:
        return None
    if len(matches) == 1 and points_line(line):
        value = label_points(matches[0].group())
        if value is None:
            return None
        return TrailingPoints(start=line_start - 1 if line_start else 0, value=value)
    last = matches[-1]
    if not last.group().startswith("(") or line[last.end() :].strip(" \t"):
        return None
    value = label_points(last.group())
    if value is None:
        return None
    start = line_start + last.start()
    while start > line_start and stripped[start - 1] in " \t":
        start -= 1
    return TrailingPoints(start=start, value=value)


def without_trailing_points(text: str, points: int | float | None) -> str:
    """The text without trailing points wording that equals the given points.

    A differing number, missing points and a text of only wording keep the
    text unchanged: there is nothing to settle, or nothing would remain.
    """
    if points is None:
        return text
    found = trailing_points(text)
    if found is None or found.value != points:
        return text
    kept = text[: found.start].rstrip()
    if not kept.strip():
        return text
    return kept


def body_without_trailing_points(
    body: tuple[NativeParagraph, ...], points: int | float | None
) -> tuple[NativeParagraph, ...]:
    """The body without trailing points wording that equals the given points.

    Only the last paragraph is examined, through its trailing run of text
    segments; a paragraph ending in a gap or a picture is never touched. A
    whole points line leaves only when its line starts inside the run. Each
    segment keeps its marks; a paragraph left with no segments is dropped. A
    body left with no text, gap or picture keeps its original paragraphs.
    """
    if points is None or not body:
        return body
    paragraph = body[-1]
    if not paragraph.segments or not isinstance(paragraph.segments[-1], NativeTextSegment):
        return body
    run: list[NativeTextSegment] = []
    for segment in reversed(paragraph.segments):
        if not isinstance(segment, NativeTextSegment):
            break
        run.append(segment)
    run.reverse()
    run_text = "".join(segment.text for segment in run)
    found = trailing_points(run_text)
    if found is None or found.value != points:
        return body
    stripped = run_text.rstrip()
    line_start = stripped.rfind("\n") + 1
    line = stripped[line_start:]
    matches = list(POINT_LABEL.finditer(line))
    if len(matches) == 1 and points_line(line):
        if line_start == 0 and len(run) != len(paragraph.segments):
            return body
    kept_text = run_text[: found.start].rstrip()
    kept: list[NativeTextSegment] = []
    remaining = len(kept_text)
    for segment in run:
        if remaining <= 0:
            break
        if len(segment.text) <= remaining:
            kept.append(segment)
            remaining -= len(segment.text)
        else:
            kept.append(segment.model_copy(update={"text": segment.text[:remaining]}))
            remaining = 0
    head = paragraph.segments[: len(paragraph.segments) - len(run)]
    settled_paragraph = paragraph.model_copy(update={"segments": (*head, *kept)})
    settled = (*body[:-1], settled_paragraph) if settled_paragraph.segments else body[:-1]
    for kept_paragraph in settled:
        for segment in kept_paragraph.segments:
            if isinstance(segment, NativeTextSegment):
                if segment.text.strip():
                    return settled
            elif isinstance(segment, (NativeGapSegment, NativeAssetSegment)):
                return settled
    return body


def with_settled_points_wording(item: NativeExamItem) -> NativeExamItem:
    """The item without trailing points wording that equals its points.

    Only the body changes; points, review and every source record stay as
    they are. A differing number, missing points or a stem of only wording
    returns the item untouched.
    """
    settled = body_without_trailing_points(item.body, item.points)
    if settled == item.body:
        return item
    return item.model_copy(update={"body": settled})
