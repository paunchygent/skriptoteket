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
from typing import Any

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

STEP_DELTA_ATTENTION_THRESHOLD = 2
STEP_DELTA_BLOCKED_THRESHOLD = 5
PERCENT_DRIFT_ATTENTION_THRESHOLD = 0.05
PERCENT_DRIFT_BLOCKED_THRESHOLD = 0.15


@dataclass(frozen=True)
class LaunchTraceSummaryArtifacts:
    """Filesystem paths for the generated launch-trace artifacts."""

    raw_artifact_path: Path
    summary_json_path: Path
    summary_markdown_path: Path


def load_trace_payload(path: Path) -> dict[str, Any]:
    """Load and return a launch-trace artifact payload from disk."""

    return json.loads(path.read_text(encoding="utf-8"))


def resolve_baseline_payload(
    baseline_artifact_path: Path,
) -> tuple[str, dict[str, Any] | None]:
    """Resolve the baseline artifact payload and return status plus payload."""

    if not baseline_artifact_path.exists():
        return BASELINE_MISSING, None

    try:
        payload = load_trace_payload(baseline_artifact_path)
    except (OSError, JSONDecodeError, ValueError):
        return BASELINE_UNREADABLE, None
    if not _is_trace_payload_shape(payload):
        return BASELINE_INCOMPATIBLE, None
    return BASELINE_AVAILABLE, payload


def build_trace_summary(
    raw_payload: dict[str, Any],
    *,
    raw_artifact_path: Path,
    baseline_artifact_path: Path = DEFAULT_BASELINE_ARTIFACT_PATH,
    baseline_override_used: bool = False,
) -> dict[str, Any]:
    """Build the deterministic operator summary for a launch-trace payload."""

    if not _is_trace_payload_shape(raw_payload):
        raise ValueError("Raw launch-trace payload is missing required top-level fields.")

    baseline_status, baseline_payload = resolve_baseline_payload(baseline_artifact_path)
    baseline_matrix = _matrix_by_case_id(baseline_payload) if baseline_payload else {}
    baseline_traces = baseline_payload.get("traces", {}) if baseline_payload else {}

    case_summaries: list[dict[str, Any]] = []
    for record in raw_payload["matrix_summaries"]:
        case_id = record["case_id"]
        trace_steps = raw_payload["traces"][case_id]
        baseline_record = baseline_matrix.get(case_id)
        baseline_steps = baseline_traces.get(case_id)
        case_summaries.append(
            _build_case_summary(
                record=record,
                trace_steps=trace_steps,
                baseline_record=baseline_record,
                baseline_steps=baseline_steps,
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
            "source_metadata": raw_payload.get("metadata", {}),
        },
        "case_summaries": case_summaries,
        "run_summary": run_summary,
    }


def write_trace_summary_artifacts(
    artifact_dir: Path,
    *,
    raw_artifact_path: Path,
    summary_payload: dict[str, Any],
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


def build_trace_summary_markdown(summary_payload: dict[str, Any]) -> str:
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


def fail_if_summary_gate_blocked(summary_payload: dict[str, Any]) -> None:
    """Raise when the run-level launch-trace decision gate is blocked."""

    run_summary = summary_payload["run_summary"]
    if run_summary["run_verdict"] != RUN_BLOCKED:
        return
    reasons = run_summary["blocked_reasons"]
    detail = "; ".join(reasons) if reasons else "no blocker detail recorded"
    raise AssertionError(f"PR-0214 launch trace decision gate blocked -> {detail}")


def _build_case_summary(
    *,
    record: dict[str, Any],
    trace_steps: list[dict[str, Any]],
    baseline_record: dict[str, Any] | None,
    baseline_steps: list[dict[str, Any]] | None,
    baseline_status: str,
) -> dict[str, Any]:
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

        _evaluate_optional_step_drift(
            field_name="handoff_to_board_step",
            current_value=record["handoff_to_board_step"],
            baseline_value=baseline_record["handoff_to_board_step"],
            blockers=blockers,
            attentions=attentions,
            anomaly_flags=anomaly_flags,
        )
        _evaluate_optional_step_drift(
            field_name="first_board_collision_step",
            current_value=record["first_board_collision_step"],
            baseline_value=baseline_record["first_board_collision_step"],
            blockers=blockers,
            attentions=attentions,
            anomaly_flags=anomaly_flags,
        )
        _evaluate_numeric_drift(
            field_name="peak_speed",
            current_value=float(record["peak_speed"]),
            baseline_value=float(baseline_record["peak_speed"]),
            blockers=blockers,
            attentions=attentions,
            anomaly_flags=anomaly_flags,
        )
        _evaluate_numeric_drift(
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
        "drift": {
            "phase_order_observed": {
                "current": record["phase_order_observed"],
                "baseline": None
                if baseline_record is None
                else baseline_record["phase_order_observed"],
                "matches_baseline": None
                if baseline_record is None
                else record["phase_order_observed"] == baseline_record["phase_order_observed"],
            },
            "handoff_to_board_step": _build_optional_step_drift(
                current_value=record["handoff_to_board_step"],
                baseline_value=None
                if baseline_record is None
                else baseline_record["handoff_to_board_step"],
            ),
            "first_board_collision_step": _build_optional_step_drift(
                current_value=record["first_board_collision_step"],
                baseline_value=None
                if baseline_record is None
                else baseline_record["first_board_collision_step"],
            ),
            "peak_speed": _build_numeric_drift(
                current_value=float(record["peak_speed"]),
                baseline_value=None
                if baseline_record is None
                else float(baseline_record["peak_speed"]),
            ),
            "max_displacement_px": _build_numeric_drift(
                current_value=float(record["max_displacement_px"]),
                baseline_value=None
                if baseline_record is None
                else float(baseline_record["max_displacement_px"]),
            ),
        },
    }


def _build_run_summary(
    case_summaries: list[dict[str, Any]], baseline_status: str
) -> dict[str, Any]:
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


def _build_spotlight_rows(trace_steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    spotlight_by_row_index: dict[int, dict[str, Any]] = {}
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


def _evaluate_optional_step_drift(
    *,
    field_name: str,
    current_value: int | None,
    baseline_value: int | None,
    blockers: list[str],
    attentions: list[str],
    anomaly_flags: list[str],
) -> None:
    if current_value is None and baseline_value is None:
        return
    if current_value is None or baseline_value is None:
        blockers.append(f"{field_name}_presence_drift")
        anomaly_flags.append(f"{field_name}_presence_drift")
        return

    delta = abs(current_value - baseline_value)
    if delta > STEP_DELTA_BLOCKED_THRESHOLD:
        blockers.append(f"{field_name}_drift_blocked")
        anomaly_flags.append(f"{field_name}_drift")
    elif delta > STEP_DELTA_ATTENTION_THRESHOLD:
        attentions.append(f"{field_name}_drift_attention")
        anomaly_flags.append(f"{field_name}_drift")


def _evaluate_numeric_drift(
    *,
    field_name: str,
    current_value: float,
    baseline_value: float,
    blockers: list[str],
    attentions: list[str],
    anomaly_flags: list[str],
) -> None:
    delta_ratio = _delta_ratio(current_value, baseline_value)
    if delta_ratio is None:
        return
    if delta_ratio > PERCENT_DRIFT_BLOCKED_THRESHOLD:
        blockers.append(f"{field_name}_drift_blocked")
        anomaly_flags.append(f"{field_name}_drift")
    elif delta_ratio > PERCENT_DRIFT_ATTENTION_THRESHOLD:
        attentions.append(f"{field_name}_drift_attention")
        anomaly_flags.append(f"{field_name}_drift")


def _build_numeric_drift(
    *,
    current_value: float,
    baseline_value: float | None,
) -> dict[str, Any]:
    delta_ratio = None if baseline_value is None else _delta_ratio(current_value, baseline_value)
    delta_absolute = None if baseline_value is None else current_value - baseline_value
    return {
        "current": current_value,
        "baseline": baseline_value,
        "delta_absolute": delta_absolute,
        "delta_ratio": delta_ratio,
    }


def _build_optional_step_drift(
    *,
    current_value: int | None,
    baseline_value: int | None,
) -> dict[str, Any]:
    if current_value is None or baseline_value is None:
        delta_absolute = None
    else:
        delta_absolute = current_value - baseline_value
    return {
        "current": current_value,
        "baseline": baseline_value,
        "delta_absolute": delta_absolute,
    }


def _delta_ratio(current_value: float, baseline_value: float) -> float | None:
    if baseline_value == 0:
        if current_value == 0:
            return 0.0
        return 1.0
    return abs(current_value - baseline_value) / abs(baseline_value)


def _matrix_by_case_id(payload: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if payload is None:
        return {}
    return {record["case_id"]: record for record in payload["matrix_summaries"]}


def _is_trace_payload_shape(payload: dict[str, Any]) -> bool:
    return "matrix_summaries" in payload and "traces" in payload


def _format_optional_int(value: int | None) -> str:
    return "-" if value is None else str(value)


def _format_percent(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value * 100:.1f}%"
