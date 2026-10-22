"""Run summary and metadata-only artifacts for the prompt-eval harness."""

from __future__ import annotations

import json
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path

from scripts.ai_prompt_eval.fixture_execution import CaseResult
from skriptoteket.protocols.llm import PromptEvalOutcome

ALL_OUTCOMES: tuple[PromptEvalOutcome, ...] = (
    "ok",
    "empty",
    "truncated",
    "over_budget",
    "timeout",
    "error",
)


def case_record(case: CaseResult) -> dict[str, object]:
    record: dict[str, object] = {
        "fixture_id": case.fixture.fixture_id,
        "capability": case.fixture.capability,
        "language": case.fixture.language,
        "http_status": case.http_status,
        "enabled": case.enabled,
        "latency_ms": case.latency_ms,
        "outcome": case.outcome,
        "template_id": case.meta.template_id,
        "system_prompt_chars": case.meta.system_prompt_chars,
        "prefix_chars": case.meta.prefix_chars,
        "suffix_chars": case.meta.suffix_chars,
        "instruction_chars": case.meta.instruction_chars,
        "selection_chars": case.meta.selection_chars,
        "response_chars": case.response_chars,
        "error_kind": case.error_kind,
        "unexpected_outcome": case.unexpected_outcome,
    }
    record.update(case.error_meta)
    return record


def _percentile(sorted_values: list[int], percentile: float) -> int:
    if not sorted_values:
        return 0
    index = int(round((len(sorted_values) - 1) * percentile))
    index = max(0, min(index, len(sorted_values) - 1))
    return sorted_values[index]


def _summarize_latency(latencies_ms: list[int]) -> dict[str, float | int | None]:
    if not latencies_ms:
        return {
            "count": 0,
            "min_ms": None,
            "max_ms": None,
            "mean_ms": None,
            "p50_ms": None,
            "p95_ms": None,
        }

    ordered = sorted(latencies_ms)
    return {
        "count": len(latencies_ms),
        "min_ms": ordered[0],
        "max_ms": ordered[-1],
        "mean_ms": round(statistics.mean(latencies_ms), 2),
        "p50_ms": _percentile(ordered, 0.50),
        "p95_ms": _percentile(ordered, 0.95),
    }


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_run_artifacts(
    *,
    run_dir: Path,
    cases: list[CaseResult],
    base_url: str,
    started_at: datetime,
    finished_at: datetime,
) -> None:
    outcome_counts: Counter[str] = Counter(case.outcome for case in cases)
    counts_by_capability: dict[str, Counter[str]] = {}
    for case in cases:
        counts_by_capability.setdefault(case.fixture.capability, Counter())[case.outcome] += 1

    summary: dict[str, object] = {
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "base_url": base_url,
        "fixture_count": len(cases),
        "capabilities": sorted({case.fixture.capability for case in cases}),
        "template_ids": sorted({c.meta.template_id for c in cases if c.meta.template_id}),
        "unexpected_outcomes": sum(1 for case in cases if case.unexpected_outcome),
        "counts": {k: outcome_counts[k] for k in ALL_OUTCOMES},
        "counts_by_capability": {
            cap: {k: counter[k] for k in ALL_OUTCOMES}
            for cap, counter in sorted(counts_by_capability.items())
        },
        "http_status_counts": dict(
            sorted(Counter(str(c.http_status) for c in cases if c.http_status is not None).items())
        ),
        "latency_all_ms": _summarize_latency([case.latency_ms for case in cases]),
        "latency_ok_ms": _summarize_latency(
            [case.latency_ms for case in cases if case.outcome == "ok"]
        ),
    }

    _write_json(run_dir / "summary.json", summary)
    with (run_dir / "cases.jsonl").open("w", encoding="utf-8") as handle:
        for case in cases:
            handle.write(json.dumps(case_record(case), ensure_ascii=False, sort_keys=True) + "\n")
