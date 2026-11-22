"""Decisions request construction and the shared result envelope."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TypedDict

from pydantic import JsonValue

from scripts.labeling_feasibility.api import (
    CallRecord,
    DecisionAnswer,
    OpenAIClient,
    answer_map,
    decision_answers,
    json_int,
    usage_details,
)

MAX_QUESTIONS_PER_REQUEST = 200  # Observed 400 above 200 on 2026-10-11.


class SlotsOutput(TypedDict):
    """Provider output of the answer_slots method: asked lines and their answers."""

    lines: list[str]
    answers: dict[str, DecisionAnswer]


def slots_output(value: JsonValue) -> SlotsOutput:
    """A saved slots output narrowed to the asked lines and their answers."""
    if not isinstance(value, dict):
        raise TypeError("slots output must be a JSON object")
    lines = value["lines"]
    if not isinstance(lines, list):
        raise TypeError("slots output lines must be a JSON array")
    asked: list[str] = []
    for line in lines:
        if not isinstance(line, str):
            raise TypeError("slots output lines must be strings")
        asked.append(line)
    return {"lines": asked, "answers": answer_map(value["answers"])}


def facit_answers(value: JsonValue) -> dict[str, DecisionAnswer]:
    """The answers of a saved facit output; the evaluator reads no other field of it."""
    if not isinstance(value, dict):
        raise TypeError("facit output must be a JSON object")
    return answer_map(value["answers"])


class RunSummary(TypedDict, total=False):
    """The summary block of a saved method file."""

    calls: float
    ok: JsonValue
    input_tokens: float
    output_tokens: float
    reasoning_tokens: JsonValue
    cost_usd: float | None
    wall_seconds: float
    sum_call_seconds: JsonValue


def _summary_number(saved: dict[str, JsonValue], key: str) -> float:
    value = saved[key]
    if not isinstance(value, (int, float)):
        raise TypeError(f"summary {key} must be a JSON number")
    return value


def run_summary(value: JsonValue) -> RunSummary:
    """A saved method summary narrowed to the fields the report reads."""
    if not isinstance(value, dict):
        raise TypeError("saved summary must be a JSON object")
    summary: RunSummary = {
        "calls": _summary_number(value, "calls"),
        "ok": value["ok"],
        "input_tokens": _summary_number(value, "input_tokens"),
        "output_tokens": _summary_number(value, "output_tokens"),
        "cost_usd": _summary_cost(value),
        "wall_seconds": _summary_number(value, "wall_seconds"),
    }
    if "reasoning_tokens" in value:
        summary["reasoning_tokens"] = value["reasoning_tokens"]
    if "sum_call_seconds" in value:
        summary["sum_call_seconds"] = value["sum_call_seconds"]
    return summary


def _summary_cost(saved: dict[str, JsonValue]) -> float | None:
    value = saved["cost_usd"]
    if value is None:
        return None
    if not isinstance(value, (int, float)):
        raise TypeError("summary cost_usd must be a JSON number or null")
    return value


def summary_ok(value: JsonValue) -> bool:
    """Whether a saved method summary records every call as ok; reads only ``ok``."""
    if not isinstance(value, dict):
        raise TypeError("saved summary must be a JSON object")
    return bool(value["ok"])


class SavedMethodFile(TypedDict, total=False):
    """A ``{summary, calls, output}`` file written for one labeling method."""

    summary: JsonValue
    output: JsonValue


def saved_method(value: JsonValue) -> SavedMethodFile:
    if not isinstance(value, dict):
        raise TypeError("saved method file must be a JSON object")
    method: SavedMethodFile = {"summary": value["summary"]}
    if "output" in value:
        method["output"] = value["output"]
    return method


@dataclass
class MethodResult:
    calls: list[CallRecord]
    output: JsonValue

    def summary(self) -> RunSummary:
        usage = [call.usage for call in self.calls]
        costs = [call.cost_usd() for call in self.calls]
        reasoning = 0
        for entry in usage:
            details = usage_details(entry.get("output_tokens_details"), tolerate_non_object=False)
            reasoning += json_int(details.get("reasoning_tokens"), "reasoning_tokens")
        return {
            "calls": len(self.calls),
            "ok": all(call.ok for call in self.calls),
            "input_tokens": sum(json_int(u.get("input_tokens"), "input_tokens") for u in usage),
            "output_tokens": sum(json_int(u.get("output_tokens"), "output_tokens") for u in usage),
            "reasoning_tokens": reasoning,
            "cost_usd": None if any(cost is None for cost in costs) else sum(c for c in costs if c),
            "wall_seconds": max((call.duration_seconds for call in self.calls), default=0.0),
            "sum_call_seconds": sum(call.duration_seconds for call in self.calls),
        }


def answers_json(answers: Mapping[str, dict[str, JsonValue]]) -> dict[str, JsonValue]:
    """The answer objects by name, as the saved method output holds them."""
    return {name: answer for name, answer in answers.items()}


async def decide(
    client: OpenAIClient,
    label: str,
    input_value: str | Sequence[Mapping[str, JsonValue]],
    questions: Sequence[Mapping[str, JsonValue]],
) -> tuple[list[CallRecord], dict[str, dict[str, JsonValue]]]:
    """Send independent questions, split into concurrent requests at the observed size limit."""
    batches = [
        questions[start : start + MAX_QUESTIONS_PER_REQUEST]
        for start in range(0, len(questions), MAX_QUESTIONS_PER_REQUEST)
    ]
    records = await asyncio.gather(
        *(
            client.decisions(label=f"{label}#{index}", input_value=input_value, questions=batch)
            for index, batch in enumerate(batches)
        )
    )
    answers: dict[str, dict[str, JsonValue]] = {}
    for record in records:
        answers.update(decision_answers(record))
    return list(records), answers
