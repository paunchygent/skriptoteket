"""Decisions request construction and the shared result envelope."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from scripts.labeling_feasibility.api import (
    CallRecord,
    OpenAIClient,
    decision_answers,
)

MAX_QUESTIONS_PER_REQUEST = 200  # Observed 400 above 200 on 2026-10-11.


@dataclass
class MethodResult:
    calls: list[CallRecord]
    output: Any

    def summary(self) -> dict[str, Any]:
        usage = [call.usage for call in self.calls]
        costs = [call.cost_usd() for call in self.calls]
        return {
            "calls": len(self.calls),
            "ok": all(call.ok for call in self.calls),
            "input_tokens": sum(int(u.get("input_tokens") or 0) for u in usage),
            "output_tokens": sum(int(u.get("output_tokens") or 0) for u in usage),
            "reasoning_tokens": sum(
                int((u.get("output_tokens_details") or {}).get("reasoning_tokens") or 0)
                for u in usage
            ),
            "cost_usd": None if any(cost is None for cost in costs) else sum(c for c in costs if c),
            "wall_seconds": max((call.duration_seconds for call in self.calls), default=0.0),
            "sum_call_seconds": sum(call.duration_seconds for call in self.calls),
        }


async def decide(
    client: OpenAIClient,
    label: str,
    input_value: str | list[dict[str, Any]],
    questions: list[dict[str, Any]],
) -> tuple[list[CallRecord], dict[str, dict[str, Any]]]:
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
    answers: dict[str, dict[str, Any]] = {}
    for record in records:
        answers.update(decision_answers(record))
    return list(records), answers
