"""Student-visible labels an export adds to an exam, in the exam's own language.

Governing decision: TASK-SKRIPT-39-05-03 D18. A Swedish exam reads "Fråga 1–15" and an
English one "Question 1–18"; an exam never shows labels in another language. The language
is read from the exam's own text by counting common function words. An exam whose text
names no known language gets labels without a word: the bare numbers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)

_WORD = re.compile(r"[^\W\d_]{2,}")


@dataclass(frozen=True)
class ExamLanguageLabels:
    """The words an export prints before question, gap and image numbers."""

    question: str = ""
    gap: str = ""
    image: str = ""
    image_of: str = ""

    def question_label(self, first: int, last: int | None = None) -> str:
        numbers = str(first) if last is None or last == first else f"{first}–{last}"
        return f"{self.question} {numbers}".strip()

    def gap_label(self, index: int) -> str:
        return f"{self.gap} {index}".strip()

    def image_alt(self, index: int, item_label: str) -> str:
        if not self.image:
            return f"{index}: {item_label}"
        return f"{self.image} {index} {self.image_of} {item_label}"


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
        ExamLanguageLabels(question="Fråga", gap="Lucka", image="Bild", image_of="till"),
    ),
    _Language(
        frozenset(
            "the and is are of to in that an for with not what which who has have "
            "can will was were or from this it".split()
        ),
        ExamLanguageLabels(question="Question", gap="Gap", image="Image", image_of="for"),
    ),
)

NUMBERS_ONLY = ExamLanguageLabels()


def exam_language_labels(document: NativeExamDocument) -> ExamLanguageLabels:
    """The labels of the language whose function words the exam text uses most."""
    lines = [document.title, *document.instructions]
    for parent in document.parents:
        lines.extend(parent.instruction)
    for item in document.items:
        lines.extend((item.title or "", *item.plain_text_lines()))
        lines.extend(choice.text for choice in item.choices)
    words = [word.casefold() for line in lines for word in _WORD.findall(line)]
    counts = [sum(word in language.function_words for word in words) for language in _LANGUAGES]
    best = max(counts)
    if best == 0 or counts.count(best) > 1:
        return NUMBERS_ONLY
    return _LANGUAGES[counts.index(best)].labels
