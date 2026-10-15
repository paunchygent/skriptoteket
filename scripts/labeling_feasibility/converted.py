"""Narrow shapes for the v14 batch recordings, limited to the fields the report reads."""

from __future__ import annotations

from typing import NotRequired, TypedDict


class ConvertedChoice(TypedDict):
    text: str
    correct: NotRequired[bool]


class ConvertedSegment(TypedDict):
    kind: NotRequired[str]
    accepted_values: NotRequired[list[str]]


class ConvertedBodyRow(TypedDict):
    segments: NotRequired[list[ConvertedSegment]]


class ConvertedItem(TypedDict):
    source_anchors: list[str]
    kind: str
    points: NotRequired[int | float | None]
    choices: NotRequired[list[ConvertedChoice]]
    body: NotRequired[list[ConvertedBodyRow]]


class ConvertedExam(TypedDict):
    items: list[ConvertedItem]
