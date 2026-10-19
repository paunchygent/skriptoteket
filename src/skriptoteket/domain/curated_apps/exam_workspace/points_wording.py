"""Trailing points wording at the end of a native exam item body.

Printed points wording ("(1 point)", "Poäng: 6 poäng") states the item's
points, never its text: ``trailing_points`` finds such wording at the end of
a text. When its number equals the item's points, ``body_without_trailing_points``
drops it from the last paragraph (keeping the word of a whole-text one-word
line, D13), and ``body_without_first_paragraph_points``
drops a parenthesised label ending the first paragraph; when the shape matches
but the number differs, the wording stays and ``leftover_points_wording``
reports it for the points-note offer. ``with_settled_points_wording`` settles
each outcome on the final item. Only the label's position and its number
decide; the stem itself is never read or rewritten.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    POINT_LABEL,
    label_points,
    points_only_line,
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
    """Points wording at the end of a text: where it starts, its number, and shape."""

    start: int
    value: int | float
    # True for the points-line shape: a last line that is only a points line.
    whole_line: bool


def trailing_points(text: str) -> TrailingPoints | None:
    """Points wording at the end of a text, or None when the end holds prose.

    Two shapes count: a last line that is only a points line, which leaves
    with its newline, and a parenthesised label ending the last line, which
    leaves with the blank space before it. A label with no number is ignored.
    When the line holds several labels, nothing counts.
    """
    stripped = text.rstrip()
    line_start = stripped.rfind("\n") + 1
    line = stripped[line_start:]
    matches = list(POINT_LABEL.finditer(line))
    if not matches:
        return None
    if len(matches) > 1:
        return None
    if points_only_line(line):
        value = label_points(matches[0].group())
        if value is None:
            return None
        return TrailingPoints(
            start=line_start - 1 if line_start else 0, value=value, whole_line=True
        )
    last = matches[-1]
    if not last.group().startswith("(") or line[last.end() :].strip(" \t"):
        return None
    value = label_points(last.group())
    if value is None:
        return None
    start = line_start + last.start()
    while start > line_start and stripped[start - 1] in " \t":
        start -= 1
    return TrailingPoints(start=start, value=value, whole_line=False)


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


def _trailing_run_wording(
    body: tuple[NativeParagraph, ...],
) -> tuple[list[NativeTextSegment], str, TrailingPoints] | None:
    """The last paragraph's trailing text run and its points wording, if any.

    Every guard sits here once: the paragraph ends in text, the run's wording is
    found, and a whole points line counts only when its line starts inside the
    run (the run holds a newline before the line, or the run is the paragraph).
    """
    if not body:
        return None
    paragraph = body[-1]
    if not paragraph.segments or not isinstance(paragraph.segments[-1], NativeTextSegment):
        return None
    run: list[NativeTextSegment] = []
    for segment in reversed(paragraph.segments):
        if not isinstance(segment, NativeTextSegment):
            break
        run.append(segment)
    run.reverse()
    run_text = "".join(segment.text for segment in run)
    found = trailing_points(run_text)
    if found is None:
        return None
    if found.whole_line:
        line_start = run_text.rstrip().rfind("\n") + 1
        if line_start == 0 and len(run) != len(paragraph.segments):
            return None
    return (run, run_text, found)


def _cut_run_text(
    body: tuple[NativeParagraph, ...], run: list[NativeTextSegment], run_text: str, start: int
) -> tuple[NativeParagraph, ...]:
    """The body with the run's text from ``start`` removed, keeping each segment's marks.

    The same cut serves the whole-line removal and the D13 whole-text word
    keep; only the start differs. A paragraph left with no segments is dropped.
    """
    paragraph = body[-1]
    kept_text = run_text[:start].rstrip()
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
    return (*body[:-1], settled_paragraph) if settled_paragraph.segments else body[:-1]


def _body_keeps_text(body: tuple[NativeParagraph, ...]) -> bool:
    """Whether any paragraph keeps text, a gap or a picture."""
    for paragraph in body:
        for placed in paragraph.segments:
            if isinstance(placed, NativeTextSegment):
                if placed.text.strip():
                    return True
            elif isinstance(placed, (NativeGapSegment, NativeAssetSegment)):
                return True
    return False


def _one_word_head_label_start(run_text: str) -> int | None:
    """The label start when a whole points-only line is the whole question text (D13).

    A last line of one letter-only word and a points label ("Max 36p",
    "Show (2 p)") leaves whole only when the question keeps other text; when
    that line is the whole question text, the word stays and only the label
    leaves, with the blank space before it. A bare label ("(2 p)"), a head
    with a colon ("Poäng:") and longer heads never count: the line stays.
    """
    stripped = run_text.rstrip()
    line_start = stripped.rfind("\n") + 1
    line = stripped[line_start:]
    matches = list(POINT_LABEL.finditer(line))
    if len(matches) != 1:
        return None
    match = matches[0]
    if re.fullmatch(r"[^\W\d_]+", line[: match.start()].strip()) is None:
        return None
    start = line_start + match.start()
    while start > line_start and stripped[start - 1] in " \t":
        start -= 1
    return start


def body_without_trailing_points(
    body: tuple[NativeParagraph, ...], points: int | float | None
) -> tuple[NativeParagraph, ...]:
    """The body without trailing points wording that equals the given points.

    Only the last paragraph is examined, through its trailing run of text
    segments; a paragraph ending in a gap or a picture is never touched. A
    whole points line leaves only when its line starts inside the run. Each
    segment keeps its marks; a paragraph left with no segments is dropped. A
    body left with no text, gap or picture keeps its original paragraphs,
    except for a whole-text line of one letter-only word and a label (D13):
    the word stays and only the label leaves.
    """
    if points is None:
        return body
    located = _trailing_run_wording(body)
    if located is None:
        return body
    run, run_text, found = located
    if found.value != points:
        return body
    settled = _cut_run_text(body, run, run_text, found.start)
    if _body_keeps_text(settled):
        return settled
    if found.whole_line:
        label_start = _one_word_head_label_start(run_text)
        if label_start is not None:
            narrowed = _cut_run_text(body, run, run_text, label_start)
            if _body_keeps_text(narrowed):
                return narrowed
    return body


def body_without_first_paragraph_points(
    body: tuple[NativeParagraph, ...], points: int | float | None
) -> tuple[NativeParagraph, ...]:
    """The body without points wording ending its first paragraph.

    A parenthesised label ending the first paragraph's last line leaves with
    the blank space before it when its number equals the given points, heading
    or not; the paragraph keeps its heading level. A one-paragraph body is the
    end-of-body rule's case, a whole points line is not this rule's case, and
    a differing number records nothing. The cut keeps each segment's marks; a
    paragraph left with no segments is dropped.
    """
    if points is None or len(body) < 2:
        return body
    located = _trailing_run_wording(body[:1])
    if located is None:
        return body
    run, run_text, found = located
    if found.whole_line or found.value != points:
        return body
    paragraph = body[0]
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
    settled = (settled_paragraph, *body[1:]) if settled_paragraph.segments else body[1:]
    for kept_paragraph in settled:
        for placed in kept_paragraph.segments:
            if isinstance(placed, NativeTextSegment):
                if placed.text.strip():
                    return settled
            elif isinstance(placed, (NativeGapSegment, NativeAssetSegment)):
                return settled
    return body


def leftover_points_wording(
    body: tuple[NativeParagraph, ...], points: int | float | None
) -> str | None:
    """The trailing points wording whose number differs from the given points.

    The same run and shape check as the removal decides: an equal number, no
    settled points, and a wording that is the whole question text record nothing.
    A bare label inside a sentence never matches, so it is never recorded.
    """
    if points is None:
        return None
    located = _trailing_run_wording(body)
    if located is None:
        return None
    run, run_text, found = located
    if found.value == points:
        return None
    paragraph = body[-1]
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
        for placed in kept_paragraph.segments:
            if isinstance(placed, NativeTextSegment):
                if placed.text.strip():
                    return run_text[found.start :].strip()
            elif isinstance(placed, (NativeGapSegment, NativeAssetSegment)):
                return run_text[found.start :].strip()
    return None


def _body_label_count(body: tuple[NativeParagraph, ...]) -> int:
    """The points labels over the joined text of every paragraph's text segments."""
    joined = "\n".join(
        "".join(
            segment.text for segment in paragraph.segments if isinstance(segment, NativeTextSegment)
        )
        for paragraph in body
    )
    return len(list(POINT_LABEL.finditer(joined)))


def with_settled_points_wording(item: NativeExamItem) -> NativeExamItem:
    """The item with its trailing points wording settled against its points.

    An equal number leaves the wording from the body's end and then from its
    first paragraph; a differing number at the end keeps the wording and records
    it in ``leftover_points_text`` for the points-note offer, while a differing
    first-paragraph number records nothing. Only the body and the leftover field
    change; points, review and every source record stay as they are. A missing
    number, a stem of only wording or a body the rule never matches returns the
    item untouched. A body holding several labels is left untouched as well:
    nothing is removed and nothing is recorded.
    """
    if _body_label_count(item.body) > 1:
        return item
    settled = body_without_trailing_points(item.body, item.points)
    if settled == item.body:
        leftover = leftover_points_wording(item.body, item.points)
        if leftover is not None:
            return item.model_copy(update={"leftover_points_text": leftover})
        settled = body_without_first_paragraph_points(item.body, item.points)
    else:
        settled = body_without_first_paragraph_points(settled, item.points)
    if settled != item.body:
        return item.model_copy(update={"body": settled})
    return item
