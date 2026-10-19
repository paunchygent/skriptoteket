"""The Swedish words an export adds to an exam.

Every export (QTI, PDF, DOCX) prints the words it adds, such as "Fråga", "Lucka", "Bild",
"Rätt svar", "Facit", "Par", "Rätt ordning" and "Rättningsmall", in Swedish, whatever
language the exam itself is written in. Exactly one label set exists. The user decision of
2026-10-18 supersedes TASK-SKRIPT-39-05-03 D18 and D21, which chose the labels by counting
function words in the exam text and printed bare numbers when no language was recognised.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)

# A printed label ends in its number or letter, optionally after a word: "Fråga 4", "a".
_PRINTED = re.compile(r"^(?:(.*\S)\s+)?(\d+|[^\W\d_])$")


@dataclass(frozen=True)
class ExamExportLabels:
    """The fixed words an export prints around question numbers, gaps, images and keys."""

    question: str
    gap: str
    image: str
    points_abbreviation: str
    answer_key: str
    correct_answer: str
    pair: str
    correct_order: str
    marking_guide: str

    def question_label(self, first: int | str, last: int | str | None = None) -> str:
        numbers = str(first) if last is None or last == first else f"{first}–{last}"
        return f"{self.question} {numbers}"

    def item_title(self, item: NativeExamItem) -> str:
        """The QTI item title: the question label such as "Fråga 3".

        Exam.net discards the QTI item title, so it carries no question wording.
        """
        return self.question_label(item.sequence)

    def printed_span(self, first: str, last: str) -> str:
        """The title over children printed first to last, such as "Fråga 1–7"."""
        first_match, last_match = _PRINTED.match(first), _PRINTED.match(last)
        if first_match and last_match and first_match.group(1) == last_match.group(1):
            word, low, high = first_match.group(1), first_match.group(2), last_match.group(2)
            if word is None:
                return self.question_label(low, high)
            return f"{word} {low}–{high}" if low != high else first
        return first if first == last else f"{first}–{last}"

    def gap_label(self, index: int) -> str:
        return f"{self.gap} {index}"

    def image_alt(self, index: int) -> str:
        """Student-visible alt text: the image word and number, never a question's number."""
        return f"{self.image} {index}"

    def points_inline(self, points: str) -> str:
        """Such as "(2 p)"."""
        return f"({points} {self.points_abbreviation})"

    def keyed(self, word: str, value: str) -> str:
        """A key line such as "Rätt svar: Beta"."""
        return f"{word}: {value}"


SWEDISH_EXAM_LABELS = ExamExportLabels(
    question="Fråga",
    gap="Lucka",
    image="Bild",
    points_abbreviation="p",
    answer_key="Facit",
    correct_answer="Rätt svar",
    pair="Par",
    correct_order="Rätt ordning",
    marking_guide="Rättningsmall",
)
