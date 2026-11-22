"""Launch-trace operational summary and decision gate for Flunk-Out Frenzy.

Purpose:
    Distill the canonical launch-to-drop trace artifact into operator-facing
    case verdicts, run verdicts, spotlight rows, and deterministic drift checks
    that remain fully traceable back to raw rows.
Relationships:
    - Consumes `.artifacts/flunk-out-frenzy-launch-to-drop/launch-to-drop-trace-matrix.json`
    - Uses the focused proof artifact under `frontend/apps/skriptoteket/.artifacts/...`
      as the pinned PR-0214 default baseline
    - Serves the focused Playwright collector in
      `scripts._playwright_flunk_out_frenzy_launch_trace_parity`
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from json import JSONDecodeError
from pathlib import Path
from typing import TypedDict

from pydantic import JsonValue

from scripts._flunk_out_frenzy_launch_trace_drift import (
    CaseDrift,
    build_case_drift,
    evaluate_numeric_drift,
    evaluate_optional_step_drift,
)
from scripts._flunk_out_frenzy_launch_trace_payload import (
    BaselineMatrixRecord,
    BaselinePayload,
    MatrixSummaryRecord,
    Number,
    TraceStep,
    has_trace_top_level_keys,
    parse_baseline_payload,
    parse_trace_payload,
)

DEFAULT_BASELINE_ARTIFACT_PATH = Path(
    "frontend/apps/skriptoteket/.artifacts/flunk-out-frenzy-launch-to-drop/"
    "launch-to-drop-trace-matrix.json"
)
SUMMARY_JSON_NAME = "launch-to-drop-trace-summary.json"
SUMMARY_MARKDOWN_NAME = "launch-to-drop-trace-summary.md"

CASE_PASS = "case_pass"
CASE_ATTENTION = "case_attention"
CASE_BLOCKED = "case_blocked"
RUN_PASS = "pass"
RUN_PASS_WITH_RESERVATIONS = "pass_with_reservations"
RUN_BLOCKED = "blocked"
BASELINE_AVAILABLE = "available"
BASELINE_MISSING = "missing"
BASELINE_UNREADABLE = "unreadable"
BASELINE_INCOMPATIBLE = "schema_incompatible"


class SpotlightRow(TypedDict):
    trace_row_index: int
    step_index: int
    phase: str
    reasons: list[str]
    seam_transition: JsonValue
    handoff_to_board_step: int | None
    first_board_collision_step: int | None


class CaseSummary(TypedDict):
    case_id: str
    hold_profile: str
    case_verdict: str
    phase_order_observed: list[str]
    sw16_exit_observed: bool
    handoff_to_board_step: int | None
    first_board_collision_step: int | None
    seam_transition_count: int
    strike_classification: str
    peak_speed: Number
    min_vy: Number
    max_displacement_px: Number
    case_blockers: list[str]
    case_attentions: list[str]
    anomaly_flags: list[str]
    spotlight_rows: list[SpotlightRow]
    drift: CaseDrift


class RunSummary(TypedDict):
    run_verdict: str
    baseline_status: str
    case_counts: dict[str, int]
    blocked_reasons: list[str]
    attention_flags: list[str]


class SummaryMetadata(TypedDict):
    generated_at_utc: str
    raw_artifact_path: str
    baseline_artifact_path: str
    baseline_override_used: bool
    baseline_status: str
    source_metadata: JsonValue


class TraceSummaryPayload(TypedDict):
    metadata: SummaryMetadata
    case_summaries: list[CaseSummary]
    run_summary: RunSummary


@dataclass(frozen=True)
class LaunchTraceSummaryArtifacts:
    """Filesystem paths for the generated launch-trace artifacts."""

    raw_artifact_path: Path
    summary_json_path: Path
    summary_markdown_path: Path


def load_trace_payload(path: Path) -> JsonValue:
    """Load and return a launch-trace artifact payload from disk."""

    payload: JsonValue = json.loads(path.read_text(encoding="utf-8"))
    return payload


def resolve_baseline_payload(
    baseline_artifact_path: Path,
) -> tuple[str, BaselinePayload | None]:
    """Resolve the baseline artifact payload and return status plus payload."""

    if not baseline_artifact_path.exists():
        return BASELINE_MISSING, None

    try:
        payload = load_trace_payload(baseline_artifact_path)
    except (OSError, JSONDecodeError, ValueError):
        return BASELINE_UNREADABLE, None
    if not has_trace_top_level_keys(payload):
        return BASELINE_INCOMPATIBLE, None
    return BASELINE_AVAILABLE, parse_baseline_payload(payload)


def build_trace_summary(
    raw_payload: JsonValue,
    *,
    raw_artifact_path: Path,
    baseline_artifact_path: Path = DEFAULT_BASELINE_ARTIFACT_PATH,
    baseline_override_used: bool = False,
) -> TraceSummaryPayload:
    """Build the deterministic operator summary for a launch-trace payload."""

    if not has_trace_top_level_keys(raw_payload):
        raise ValueError("Raw launch-trace payload is missing required top-level fields.")
    payload = parse_trace_payload(raw_payload)

    baseline_status, baseline = resolve_baseline_payload(baseline_artifact_path)
    baseline_matrix = {} if baseline is None else baseline["matrix_summaries"]
    baseline_traces = {} if baseline is None else baseline["traces"]

    case_summaries: list[CaseSummary] = []
    for record in payload["matrix_summaries"]:
        case_id = record["case_id"]
        case_summaries.append(
            _build_case_summary(
                record=record,
                trace_steps=payload["traces"][case_id],
                baseline_record=baseline_matrix.get(case_id),
                baseline_steps=baseline_traces.get(case_id),
                baseline_status=baseline_status,
            )
        )

    run_summary = _build_run_summary(case_summaries, baseline_status)
    return {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "raw_artifact_path": str(raw_artifact_path),
            "baseline_artifact_path": str(baseline_artifact_path),
            "baseline_override_used": baseline_override_used,
            "baseline_status": baseline_status,
            "source_metadata": payload.get("metadata", {}),
        },
        "case_summaries": case_summaries,
        "run_summary": run_summary,
    }


def write_trace_summary_artifacts(
    artifact_dir: Path,
    *,
    raw_artifact_path: Path,
    summary_payload: TraceSummaryPayload,
) -> LaunchTraceSummaryArtifacts:
    """Persist the summary JSON/Markdown artifacts and return their paths."""

    artifact_dir.mkdir(parents=True, exist_ok=True)
    summary_json_path = artifact_dir / SUMMARY_JSON_NAME
    summary_markdown_path = artifact_dir / SUMMARY_MARKDOWN_NAME
    summary_json_path.write_text(
        f"{json.dumps(summary_payload, indent=2)}\n",
        encoding="utf-8",
    )
    summary_markdown_path.write_text(
        build_trace_summary_markdown(summary_payload),
        encoding="utf-8",
    )
    return LaunchTraceSummaryArtifacts(
        raw_artifact_path=raw_artifact_path,
        summary_json_path=summary_json_path,
        summary_markdown_path=summary_markdown_path,
    )


def build_trace_summary_markdown(summary_payload: TraceSummaryPayload) -> str:
    """Render the operator summary payload as concise Markdown."""

    run_summary = summary_payload["run_summary"]
    metadata = summary_payload["metadata"]
    lines = [
        "# Launch Trace Summary",
        "",
        f"- Run verdict: `{run_summary['run_verdict']}`",
        f"- Baseline status: `{metadata['baseline_status']}`",
        f"- Raw artifact: `{metadata['raw_artifact_path']}`",
        f"- Baseline artifact: `{metadata['baseline_artifact_path']}`",
        "",
        "## Case Verdicts",
        "",
        "| Case | Verdict | Handoff | Collision | Seams | Peak drift | Disp drift | Flags |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for case in summary_payload["case_summaries"]:
        flags = ", ".join(case["anomaly_flags"]) if case["anomaly_flags"] else "-"
        lines.append(
            "| "
            f"{case['case_id']} | {case['case_verdict']} | "
            f"{_format_optional_int(case['handoff_to_board_step'])} | "
            f"{_format_optional_int(case['first_board_collision_step'])} | "
            f"{case['seam_transition_count']} | "
            f"{_format_percent(case['drift']['peak_speed']['delta_ratio'])} | "
            f"{_format_percent(case['drift']['max_displacement_px']['delta_ratio'])} | "
            f"{flags} |"
        )

    lines.extend(["", "## Spotlight Rows", ""])
    for case in summary_payload["case_summaries"]:
        lines.append(f"### {case['case_id']}")
        if not case["spotlight_rows"]:
            lines.append("- No spotlight rows.")
            lines.append("")
            continue
        for row in case["spotlight_rows"]:
            reasons = ", ".join(row["reasons"])
            lines.append(
                "- "
                f"`row {row['trace_row_index']}` / `step {row['step_index']}` "
                f"`{row['phase']}` reasons: {reasons}"
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def fail_if_summary_gate_blocked(summary_payload: TraceSummaryPayload) -> None:
    """Raise when the run-level launch-trace decision gate is blocked."""

    run_summary = summary_payload["run_summary"]
    if run_summary["run_verdict"] != RUN_BLOCKED:
        return
    reasons = run_summary["blocked_reasons"]
    detail = "; ".join(reasons) if reasons else "no blocker detail recorded"
    raise AssertionError(f"PR-0214 launch trace decision gate blocked -> {detail}")


def _build_case_summary(
    *,
    record: MatrixSummaryRecord,
    trace_steps: list[TraceStep],
    baseline_record: BaselineMatrixRecord | None,
    baseline_steps: list[TraceStep] | None,
    baseline_status: str,
) -> CaseSummary:
    seam_transition_count = sum(step["seam_transition"] is not None for step in trace_steps)
    spotlight_rows = _build_spotlight_rows(trace_steps)
    anomaly_flags: list[str] = []
    blockers = list(record["invariant_violations"])
    attentions: list[str] = []

    if baseline_status != BASELINE_AVAILABLE:
        blockers.append(f"baseline_unavailable:{baseline_status}")
    elif baseline_record is None or baseline_steps is None:
        blockers.append("baseline_missing_case")
    else:
        phase_order_current = record["phase_order_observed"]
        phase_order_baseline = baseline_record["phase_order_observed"]
        if phase_order_current != phase_order_baseline:
            blockers.append("phase_order_drift")
            anomaly_flags.append("phase_order_drift")

        if record["strike_classification"] != baseline_record["strike_classification"]:
            blockers.append("strike_classification_drift")
            anomaly_flags.append("strike_classification_drift")

        if seam_transition_count != sum(
            step["seam_transition"] is not None for step in baseline_steps
        ):
            blockers.append("seam_transition_count_drift")
            anomaly_flags.append("seam_transition_count_drift")

        evaluate_optional_step_drift(
            field_name="handoff_to_board_step",
            current_value=record["handoff_to_board_step"],
            baseline_value=baseline_record["handoff_to_board_step"],
            blockers=blockers,
            attentions=attentions,
            anomaly_flags=anomaly_flags,
        )
        evaluate_optional_step_drift(
            field_name="first_board_collision_step",
            current_value=record["first_board_collision_step"],
            baseline_value=baseline_record["first_board_collision_step"],
            blockers=blockers,
            attentions=attentions,
            anomaly_flags=anomaly_flags,
        )
        evaluate_numeric_drift(
            field_name="peak_speed",
            current_value=float(record["peak_speed"]),
            baseline_value=float(baseline_record["peak_speed"]),
            blockers=blockers,
            attentions=attentions,
            anomaly_flags=anomaly_flags,
        )
        evaluate_numeric_drift(
            field_name="max_displacement_px",
            current_value=float(record["max_displacement_px"]),
            baseline_value=float(baseline_record["max_displacement_px"]),
            blockers=blockers,
            attentions=attentions,
            anomaly_flags=anomaly_flags,
        )

    case_verdict = CASE_PASS
    if blockers:
        case_verdict = CASE_BLOCKED
    elif attentions:
        case_verdict = CASE_ATTENTION

    return {
        "case_id": record["case_id"],
        "hold_profile": record["hold_profile"],
        "case_verdict": case_verdict,
        "phase_order_observed": record["phase_order_observed"],
        "sw16_exit_observed": record["sw16_exit_observed"],
        "handoff_to_board_step": record["handoff_to_board_step"],
        "first_board_collision_step": record["first_board_collision_step"],
        "seam_transition_count": seam_transition_count,
        "strike_classification": record["strike_classification"],
        "peak_speed": record["peak_speed"],
        "min_vy": record["min_vy"],
        "max_displacement_px": record["max_displacement_px"],
        "case_blockers": blockers,
        "case_attentions": attentions,
        "anomaly_flags": sorted(set(anomaly_flags)),
        "spotlight_rows": spotlight_rows,
        "drift": build_case_drift(record, baseline_record),
    }


def _build_run_summary(case_summaries: list[CaseSummary], baseline_status: str) -> RunSummary:
    counts = {
        CASE_PASS: sum(case["case_verdict"] == CASE_PASS for case in case_summaries),
        CASE_ATTENTION: sum(case["case_verdict"] == CASE_ATTENTION for case in case_summaries),
        CASE_BLOCKED: sum(case["case_verdict"] == CASE_BLOCKED for case in case_summaries),
    }
    blocked_reasons = sorted(
        {reason for case in case_summaries for reason in case["case_blockers"]}
    )
    attention_flags = sorted(
        {reason for case in case_summaries for reason in case["case_attentions"]}
    )

    run_verdict = RUN_PASS
    if baseline_status != BASELINE_AVAILABLE or counts[CASE_BLOCKED] > 0:
        run_verdict = RUN_BLOCKED
    elif counts[CASE_ATTENTION] > 0:
        run_verdict = RUN_PASS_WITH_RESERVATIONS

    return {
        "run_verdict": run_verdict,
        "baseline_status": baseline_status,
        "case_counts": counts,
        "blocked_reasons": blocked_reasons,
        "attention_flags": attention_flags,
    }


def _build_spotlight_rows(trace_steps: list[TraceStep]) -> list[SpotlightRow]:
    spotlight_by_row_index: dict[int, SpotlightRow] = {}
    seen_phases: set[str] = set()
    first_handoff_row: int | None = None
    first_preimpact_row: int | None = None
    first_collision_row: int | None = None

    for row_index, step in enumerate(trace_steps):
        reasons: list[str] = []
        phase = step["phase"]
        if phase not in seen_phases:
            seen_phases.add(phase)
            reasons.append(f"first_phase:{phase}")
        if step["seam_transition"] is not None:
            reasons.append("seam_transition")
        if first_handoff_row is None and (
            phase == "handoff_to_board" or step["handoff_to_board_step"] is not None
        ):
            first_handoff_row = row_index
            reasons.append("first_handoff_to_board")
        if first_preimpact_row is None and phase == "board_drop_preimpact":
            first_preimpact_row = row_index
            reasons.append("first_board_drop_preimpact")
        if first_collision_row is None and step["first_board_collision_step"] is not None:
            first_collision_row = row_index
            reasons.append("first_board_collision")

        if not reasons:
            continue
        spotlight_by_row_index[row_index] = {
            "trace_row_index": row_index,
            "step_index": step["step_index"],
            "phase": phase,
            "reasons": reasons,
            "seam_transition": step["seam_transition"],
            "handoff_to_board_step": step["handoff_to_board_step"],
            "first_board_collision_step": step["first_board_collision_step"],
        }

    return [spotlight_by_row_index[index] for index in sorted(spotlight_by_row_index)]


def _format_optional_int(value: int | None) -> str:
    return "-" if value is None else str(value)


def _format_percent(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value * 100:.1f}%"
