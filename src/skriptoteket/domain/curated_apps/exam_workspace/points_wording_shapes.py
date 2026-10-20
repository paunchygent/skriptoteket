"""What counts as trailing points wording, on strings only.

Printed points wording ("(1 point)", "Poäng: 6 poäng") states the item's
points, never its text: ``trailing_points`` finds such wording at the end of
a text. A points-only line is cut by its head shape, which decides bare and
parenthesised labels alike: an empty or colon head leaves whole, a one-word
head without a colon keeps its word (D12 Correction).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    POINT_LABEL,
    label_points,
    points_only_line,
)


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


def one_word_head_label_start(run_text: str) -> int | None:
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


def _points_only_word_head_label_start(run_text: str) -> int | None:
    """The label start when a points-only last line keeps a one-word head.

    D12 fourth extension: an empty head or one ending in a colon leaves whole,
    so only a one-letter-word head without a colon ("Tempus", "Max") trims to
    the word; a longer head never reaches here, since a points-only line holds
    at most a two-word head ending in a colon.
    """
    stripped = run_text.rstrip()
    line_start = stripped.rfind("\n") + 1
    line = stripped[line_start:]
    if not points_only_line(line):
        return None
    matches = list(POINT_LABEL.finditer(line))
    if len(matches) != 1:
        return None
    match = matches[0]
    head = line[: match.start()]
    if not head.strip() or head.rstrip().endswith(":"):
        return None
    if re.fullmatch(r"[^\W\d_]+", head.strip()) is None:
        return None
    start = line_start + match.start()
    while start > line_start and stripped[start - 1] in " \t":
        start -= 1
    return start


def first_paragraph_bare_only_value(run_text: str) -> int | float | None:
    """The value when a first paragraph holds only points wording.

    D12 extension E: ``heading_level`` comes from the Word heading style, so a
    heading chunk without a style level reaches the final gate as a plain first
    paragraph holding only its points wording. A points-only line with an empty
    or colon head ("Poäng: 2 poäng", "Max poäng: 6 p") or a bare label as the
    paragraph's only words ("1 point") counts; a one-word head without a colon
    ("Tempus 3 poäng", "Max 36p") keeps its word through the label trim, a
    paragraph with other words ("Uppgift 3 – 4 poäng",
    "Beskriv fotosyntesen, 2 p") and a parenthesised label (the
    parenthesised rule's case) never count.
    """
    stripped = run_text.strip()
    matches = list(POINT_LABEL.finditer(stripped))
    if len(matches) != 1:
        return None
    match = matches[0]
    if match.group().startswith("("):
        return None
    if points_only_line(stripped):
        if _points_only_word_head_label_start(stripped) is not None:
            return None
        return label_points(match.group())
    if stripped[: match.start()].strip():
        return None
    if stripped[match.end() :].strip(" \t.,;:!?"):
        return None
    return label_points(match.group())


# One trailing dash or colon with the blank space before it, left by a
# bare-label cut at the end of a heading paragraph ("Uppgift 3 –" gives
# "Uppgift 3"; an attached colon is stripped the same way, "Fråga 2:").
HEADING_TRAILING_SEPARATOR = re.compile(r"[ \t]*[–—\-:]$")
# A dash or colon with the blank space after it, before a bare label at the
# end of a heading line ("Uppgift 3 – 4 poäng", "Fråga 2: 1 point").
HEADING_BARE_LABEL_SEPARATOR = re.compile(r"[–—\-:][ \t]+$")


def _whole_line_start(run_text: str) -> int:
    """The cut start that drops the run's whole last line with its newline."""
    stripped = run_text.rstrip()
    line_start = stripped.rfind("\n") + 1
    return line_start - 1 if line_start else 0


def points_only_line_start(run_text: str) -> int:
    """The cut start for a last line that is a points-only line, by head shape.

    One head-shape decision for the heading and first-paragraph paths: a
    one-word head without a colon keeps its word and loses only the label,
    while an empty or colon head leaves the whole line.
    """
    label_start = _points_only_word_head_label_start(run_text)
    if label_start is not None:
        return label_start
    return _whole_line_start(run_text)
