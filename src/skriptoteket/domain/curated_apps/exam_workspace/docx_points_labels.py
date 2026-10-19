"""The label a printed total carries, in Swedish and English (TASK-SKRIPT-39-04-11 D2, D3).

A line that prints a total is classified by its own label, never by which other lines
exist: a part label ("Del 2: 15 poäng", "Part E") opens a part; an exam label ("Total: 36
poäng", "Max 40 p", "Prov i svenska, 40 poäng") makes it an exam-total candidate; a
question label ("Poäng: 2 poäng") marks a question's own points. A numbered heading such
as "2. Tempus (3 p)" carries no label: as a heading it opens a part over the questions
under it. A line without one of these labels is unlabelled.

A summary line names several parts with a total each ("Del 1: Morfem (20 p) • Del 2: ...");
``part_totals`` reads them.
"""

import re
from itertools import pairwise
from typing import Literal

from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    POINTS_MENTION,
    text_points,
)

PointsLabel = Literal["part", "exam", "question"]

_PART_LABEL = r"\b(?:del|part|avsnitt|section|uppgiftsdel)\s+(\d+[a-zåäö]?|[a-zåäö])\b"
_PART = re.compile(r"^\s*" + _PART_LABEL, re.IGNORECASE)
_PART_ANYWHERE = re.compile(_PART_LABEL, re.IGNORECASE)
_EXAM = re.compile(
    r"^\s*(?:total\s+points|totalt?|summa|maxpoäng|max|prov|exam|test|tentamen)\b",
    re.IGNORECASE,
)
_QUESTION = re.compile(r"^\s*(?:poäng|points?)\s*:", re.IGNORECASE)
# A summary segment's trailing separator run: blank space, separators and dashes.
_SEGMENT_END = re.compile(r"[ \t•·|–—-]+$")


def points_label(text: str) -> PointsLabel | None:
    """The label that opens the line's text, or None for an unlabelled line."""
    if _PART.match(text):
        return "part"
    if _EXAM.match(text):
        return "exam"
    if _QUESTION.match(text):
        return "question"
    return None


def part_identity(text: str) -> str | None:
    """The part a part-labelled line names, its number or letter ("3" in "Part 3, Question
    1"), or None for a line without a part label."""
    match = _PART.match(text)
    return match.group(1).lower() if match else None


def part_totals(text: str) -> tuple[tuple[str, int | float], ...]:
    """Each part a summary line names with its total, such as ("1", 20) for "Del 1: Morfem
    (20 p)", in line order.

    The line splits at every part label; a segment that prints exactly one points label
    gives its part's total. Each segment first loses its trailing separator run, so a
    label before the " • " separator still ends its segment. A segment that mentions
    points twice, such as "Del 1: 4 p eller 6 p", prints no single total. A line with
    fewer than two such segments is no summary: ().
    """
    starts = [match.start() for match in _PART_ANYWHERE.finditer(text)]
    totals: list[tuple[str, int | float]] = []
    for start, end in pairwise([*starts, len(text)]):
        segment = _SEGMENT_END.sub("", text[start:end])
        identity = _PART_ANYWHERE.match(segment)
        total = text_points(segment)
        if identity is not None and total is not None and len(POINTS_MENTION.findall(segment)) == 1:
            totals.append((identity.group(1).lower(), total))
    return tuple(totals) if len(totals) >= 2 else ()
