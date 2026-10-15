"""Saved grouping structure shared by the provider grouping methods."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Question:
    id: str
    anchors: list[str]
    key_anchors: list[str] = field(default_factory=list)
    subpart_anchors: list[str] = field(default_factory=list)


@dataclass
class Context:
    anchor: str
    scope: str
    owner: str
    governs: list[str]


@dataclass
class Grouping:
    method: str
    questions: list[Question]
    contexts: list[Context]
    title: list[str]
    other: list[str]
    invalid_anchors: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "questions": [vars(question) for question in self.questions],
            "contexts": [vars(context) for context in self.contexts],
            "title": self.title,
            "other": self.other,
            "invalid_anchors": self.invalid_anchors,
        }

    @classmethod
    def from_json(cls, saved: dict[str, Any]) -> Grouping:
        return cls(
            method=saved["method"],
            questions=[Question(**question) for question in saved["questions"]],
            contexts=[Context(**context) for context in saved["contexts"]],
            title=saved["title"],
            other=saved["other"],
            invalid_anchors=saved["invalid_anchors"],
        )
