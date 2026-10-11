"""Typed saved inputs and measurement records for the live labeler driver."""

from __future__ import annotations

from pydantic import JsonValue
from typing_extensions import NotRequired, TypedDict


class GroupedQuestion(TypedDict):
    id: str
    anchors: list[str]
    key_anchors: list[str]


class GoverningContext(TypedDict):
    anchor: str
    governs: list[str]
    scope: str


class SavedGrouping(TypedDict):
    questions: list[GroupedQuestion]
    contexts: list[GoverningContext]
    title: list[str]


class GroupingRecord(TypedDict):
    output: SavedGrouping


class ItemRecord(TypedDict):
    item_id: str
    source_text: str


class ChoiceRecord(TypedDict):
    value: str
    description: str


class QuestionRecord(TypedDict):
    type: str
    name: str
    instructions: str
    choices: list[ChoiceRecord]


class RequestRecord(TypedDict):
    model: str
    input: str
    questions: list[QuestionRecord]


class ExchangeRecord(TypedDict):
    request: RequestRecord
    status_code: int
    duration_seconds: float
    start_seconds: float
    finished_seconds: float
    headers: dict[str, str]
    body: JsonValue


class ResultRecord(TypedDict):
    item_id: str
    label: str
    probability: float
    threshold: float
    route: str
    refused: bool
    probabilities: dict[str, float]
    first_pass: ResultRecord | None


class UsageRecord(TypedDict):
    input_tokens: int | None
    requests: int
    attempts: int
    cost_usd: float | None


class LabelingRecord(TypedDict):
    usage: UsageRecord
    results: list[ResultRecord]


class ErrorRecord(TypedDict):
    code: str
    status_code: int | None


class RunSummary(TypedDict):
    name: str
    items: int
    wall_seconds: float
    start_offset: float
    first_pass_wall_seconds: float
    usage: NotRequired[UsageRecord]
    error: NotRequired[ErrorRecord]


class RunRecord(TypedDict):
    name: str
    items: list[ItemRecord]
    exchanges: list[ExchangeRecord]
    wall_seconds: float
    start_offset: float
    first_pass_wall_seconds: float
    usage: NotRequired[UsageRecord]
    results: NotRequired[list[ResultRecord]]
    error: NotRequired[ErrorRecord]


class CorpusSummary(TypedDict):
    corpus_wall_seconds: float
    first_pass_wall_seconds: float
    runs: list[RunSummary]
