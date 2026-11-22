"""Baseline drift checks for the Flunk-Out Frenzy launch-trace summary.

Purpose:
    Compare current launch-trace record fields with the pinned baseline and
    record blockers, attentions, and per-field drift values.
Relationships:
    - Serves `scripts._flunk_out_frenzy_launch_trace_summary`
"""

from __future__ import annotations

from typing import TypedDict

from scripts._flunk_out_frenzy_launch_trace_payload import (
    BaselineMatrixRecord,
    MatrixSummaryRecord,
)

STEP_DELTA_ATTENTION_THRESHOLD = 2
STEP_DELTA_BLOCKED_THRESHOLD = 5
PERCENT_DRIFT_ATTENTION_THRESHOLD = 0.05
PERCENT_DRIFT_BLOCKED_THRESHOLD = 0.15


class PhaseOrderDrift(TypedDict):
    current: list[str]
    baseline: list[str] | None
    matches_baseline: bool | None


class OptionalStepDrift(TypedDict):
    current: int | None
    baseline: int | None
    delta_absolute: int | None


class NumericDrift(TypedDict):
    current: float
    baseline: float | None
    delta_absolute: float | None
    delta_ratio: float | None


class CaseDrift(TypedDict):
    phase_order_observed: PhaseOrderDrift
    handoff_to_board_step: OptionalStepDrift
    first_board_collision_step: OptionalStepDrift
    peak_speed: NumericDrift
    max_displacement_px: NumericDrift


def build_case_drift(
    record: MatrixSummaryRecord, baseline_record: BaselineMatrixRecord | None
) -> CaseDrift:
    """Return every per-field drift value of one case against its baseline record."""

    if baseline_record is None:
        return {
            "phase_order_observed": {
                "current": record["phase_order_observed"],
                "baseline": None,
                "matches_baseline": None,
            },
            "handoff_to_board_step": build_optional_step_drift(
                current_value=record["handoff_to_board_step"], baseline_value=None
            ),
            "first_board_collision_step": build_optional_step_drift(
                current_value=record["first_board_collision_step"], baseline_value=None
            ),
            "peak_speed": build_numeric_drift(
                current_value=float(record["peak_speed"]), baseline_value=None
            ),
            "max_displacement_px": build_numeric_drift(
                current_value=float(record["max_displacement_px"]), baseline_value=None
            ),
        }
    return {
        "phase_order_observed": {
            "current": record["phase_order_observed"],
            "baseline": baseline_record["phase_order_observed"],
            "matches_baseline": record["phase_order_observed"]
            == baseline_record["phase_order_observed"],
        },
        "handoff_to_board_step": build_optional_step_drift(
            current_value=record["handoff_to_board_step"],
            baseline_value=baseline_record["handoff_to_board_step"],
        ),
        "first_board_collision_step": build_optional_step_drift(
            current_value=record["first_board_collision_step"],
            baseline_value=baseline_record["first_board_collision_step"],
        ),
        "peak_speed": build_numeric_drift(
            current_value=float(record["peak_speed"]),
            baseline_value=float(baseline_record["peak_speed"]),
        ),
        "max_displacement_px": build_numeric_drift(
            current_value=float(record["max_displacement_px"]),
            baseline_value=float(baseline_record["max_displacement_px"]),
        ),
    }


def evaluate_optional_step_drift(
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


def evaluate_numeric_drift(
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


def build_numeric_drift(
    *,
    current_value: float,
    baseline_value: float | None,
) -> NumericDrift:
    delta_ratio = None if baseline_value is None else _delta_ratio(current_value, baseline_value)
    delta_absolute = None if baseline_value is None else current_value - baseline_value
    return {
        "current": current_value,
        "baseline": baseline_value,
        "delta_absolute": delta_absolute,
        "delta_ratio": delta_ratio,
    }


def build_optional_step_drift(
    *,
    current_value: int | None,
    baseline_value: int | None,
) -> OptionalStepDrift:
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
