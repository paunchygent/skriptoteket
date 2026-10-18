"""The label a printed total carries, in Swedish and English (TASK-SKRIPT-39-04-11 D2, D3).

A line that prints a total is classified by its own label, never by which other lines
exist: a part label ("Del 2: 15 poäng", "Part E") opens a part; an exam label ("Total: 36
poäng", "Max 40 p", "Prov i svenska, 40 poäng") makes it an exam-total candidate; a
question label ("Poäng: 2 poäng") marks a question's own points. A numbered heading such
as "2. Tempus (3 p)" carries no label: as a heading it opens a part over the questions
under it. A line without one of these labels is unlabelled.
"""

import re
from typing import Literal

PointsLabel = Literal["part", "exam", "question"]

_PART = re.compile(
    r"^\s*(?:del|part|avsnitt|section|uppgiftsdel)\s+(\d+[a-zåäö]?|[a-zåäö])\b",
    re.IGNORECASE,
)
_EXAM = re.compile(
    r"^\s*(?:total\s+points|totalt?|summa|maxpoäng|max|prov|exam|test|tentamen)\b",
    re.IGNORECASE,
)
_QUESTION = re.compile(r"^\s*(?:poäng|points?)\s*:", re.IGNORECASE)


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
