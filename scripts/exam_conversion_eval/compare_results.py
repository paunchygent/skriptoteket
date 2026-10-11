"""What a comparison reports: mismatches per question, the exam title and the exam verdict."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Literal

Principle = Literal[
    "response_kind",
    "scoring",
    "points",
    "no_answer_leakage",
    "content_present",
    "gold",
]
PRINCIPLES: tuple[Principle, ...] = (
    "response_kind",
    "scoring",
    "points",
    "no_answer_leakage",
    "content_present",
)


@dataclass(frozen=True)
class FieldMismatch:
    principle: Principle
    reason: str
    expected: object
    actual: object


@dataclass(frozen=True)
class ItemComparison:
    """One question: a standalone item or a child of a parent."""

    index: int
    source_label: str
    mismatches: tuple[FieldMismatch, ...]

    @property
    def passed(self) -> bool:
        return not self.mismatches

    def failed_principles(self) -> frozenset[Principle]:
        return frozenset(mismatch.principle for mismatch in self.mismatches)


@dataclass(frozen=True)
class TitleComparison:
    """D12: the exam heading, or the heading with its printed subtitle, is the title."""

    gold: str
    actual: str | None
    passed: bool


@dataclass(frozen=True)
class ExamComparison:
    confirmed: bool
    confirmation_note: str | None
    items: tuple[ItemComparison, ...]
    title: TitleComparison

    @property
    def unconfirmed(self) -> bool:
        return not self.confirmed

    @property
    def passed(self) -> bool:
        """Substantive result; confirmation status remains separate metadata."""
        return self.title.passed and all(item.passed for item in self.items)

    def failures_by_principle(self) -> dict[Principle, int]:
        """How many questions fail each principle."""
        counts = Counter(p for item in self.items for p in item.failed_principles())
        return {principle: counts[principle] for principle in PRINCIPLES}
