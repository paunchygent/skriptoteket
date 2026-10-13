"""Student-visible labels an export adds to an exam, in the exam's own language.

Governing decisions: TASK-SKRIPT-39-05-03 D18 and D21. A Swedish exam reads "Fråga 1–15"
and an English one "Question 1–18"; no export shows fixed words in another language. The
language is read from the exam's own text by counting common function words. An exam whose
text names no known language gets labels without a word: bare numbers and symbols.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamItem,
)

_WORD = re.compile(r"[^\W\d_]{2,}")
# A printed label ends in its number or letter, optionally after a word: "Question 4", "a".
_PRINTED = re.compile(r"^(?:(.*\S)\s+)?(\d+|[^\W\d_])$")


@dataclass(frozen=True)
class ExamLanguageLabels:
    """The fixed words an export prints around question numbers, gaps, images and keys."""

    language: str = ""
    question: str = ""
    gap: str = ""
    image: str = ""
    points: str = ""
    points_unit: str = ""
    points_missing: str = "–"
    answer_key: str = "✓"
    correct_answer: str = ""
    pair: str = ""
    marking_guide: str = ""

    def question_label(self, first: int | str, last: int | str | None = None) -> str:
        numbers = str(first) if last is None or last == first else f"{first}–{last}"
        return f"{self.question} {numbers}".strip()

    def item_title(self, item: NativeExamItem) -> str:
        """The QTI item title: the question label in the exam's language, such as "Fråga 3".

        Exam.net discards the QTI item title, so it carries no question wording.
        """
        return self.question_label(item.sequence)

    def printed_span(self, first: str, last: str) -> str:
        """The title over children printed first to last, such as "Question 1–7"."""
        first_match, last_match = _PRINTED.match(first), _PRINTED.match(last)
        if first_match and last_match and first_match.group(1) == last_match.group(1):
            word, low, high = first_match.group(1), first_match.group(2), last_match.group(2)
            if word is None:
                return self.question_label(low, high)
            return f"{word} {low}–{high}" if low != high else first
        return first if first == last else f"{first}–{last}"

    def gap_label(self, index: int) -> str:
        return f"{self.gap} {index}".strip()

    def image_alt(self, index: int) -> str:
        """Student-visible alt text: the image word and number, never a question's number."""
        return f"{self.image} {index}".strip()

    def points_line(self, points: str | None) -> str:
        """Such as "Poäng: 2 poäng" or "Points: 2"; "(2)" without a known language."""
        value = self.points_missing if points is None else f"{points} {self.points_unit}".strip()
        return f"{self.points}: {value}" if self.points else f"({value})"

    def keyed(self, word: str, value: str) -> str:
        """A key line such as "Rätt svar: Beta"; the bare value without a known language."""
        return f"{word}: {value}" if word else value


@dataclass(frozen=True)
class _Language:
    function_words: frozenset[str]
    labels: ExamLanguageLabels


_LANGUAGES = (
    _Language(
        frozenset(
            "och att det som är en ett på för med av inte till om vad vilken vilka "
            "har kan ska den de jag du var när eller också från".split()
        ),
        ExamLanguageLabels(
            language="sv",
            question="Fråga",
            gap="Lucka",
            image="Bild",
            points="Poäng",
            points_unit="poäng",
            points_missing="saknas",
            answer_key="Facit",
            correct_answer="Rätt svar",
            pair="Par",
            marking_guide="Rättningsmall",
        ),
    ),
    _Language(
        frozenset(
            "the and is are of to in that an for with not what which who has have "
            "can will was were or from this it".split()
        ),
        ExamLanguageLabels(
            language="en",
            question="Question",
            gap="Gap",
            image="Image",
            points="Points",
            points_missing="missing",
            answer_key="Answer key",
            correct_answer="Correct answer",
            pair="Pair",
            marking_guide="Marking guide",
        ),
    ),
)

NUMBERS_ONLY = ExamLanguageLabels()


def exam_language_labels(document: NativeExamDocument) -> ExamLanguageLabels:
    """The labels of the language whose function words the exam text uses most."""
    lines = [document.title, *document.instructions]
    for parent in document.parents:
        lines.extend(parent.instruction)
    for item in document.items:
        lines.extend(item.plain_text_lines())
        lines.extend(choice.text for choice in item.choices)
    words = [word.casefold() for line in lines for word in _WORD.findall(line)]
    counts = [sum(word in language.function_words for word in words) for language in _LANGUAGES]
    best = max(counts)
    if best == 0 or counts.count(best) > 1:
        return NUMBERS_ONLY
    return _LANGUAGES[counts.index(best)].labels
