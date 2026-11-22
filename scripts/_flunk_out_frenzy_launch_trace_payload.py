"""Typed parse layer for the Flunk-Out Frenzy launch-to-drop trace artifact.

Purpose:
    Narrow the browser-produced launch-trace artifact (`LaunchToDropTraceArtifactPayload`
    in `launchTraceContract.ts`) into named types holding only the fields the
    operator summary reads, so the summary never touches raw JSON.
Relationships:
    - Consumed by `scripts._flunk_out_frenzy_launch_trace_summary`
"""

from __future__ import annotations

from typing import NotRequired, TypedDict

from pydantic import JsonValue

type Number = int | float


class TraceStep(TypedDict):
    """One canonical launch-trace step row; only the keys the summary reads."""

    step_index: int
    phase: str
    seam_transition: JsonValue
    handoff_to_board_step: int | None
    first_board_collision_step: int | None


class BaselineMatrixRecord(TypedDict):
    """`matrix_summaries` fields the baseline drift checks read."""

    case_id: str
    phase_order_observed: list[str]
    strike_classification: str
    handoff_to_board_step: int | None
    first_board_collision_step: int | None
    peak_speed: Number
    max_displacement_px: Number


class MatrixSummaryRecord(BaselineMatrixRecord):
    """`matrix_summaries` fields the summary reads for the current run."""

    hold_profile: str
    sw16_exit_observed: bool
    min_vy: Number
    invariant_violations: list[str]


class LaunchTracePayload(TypedDict):
    """Launch-trace artifact payload after the top-level shape check."""

    matrix_summaries: list[MatrixSummaryRecord]
    traces: dict[str, list[TraceStep]]
    metadata: NotRequired[JsonValue]


class BaselinePayload(TypedDict):
    """Pinned baseline artifact: only the fields the drift checks read."""

    matrix_summaries: dict[str, BaselineMatrixRecord]
    traces: dict[str, list[TraceStep]]


def has_trace_top_level_keys(payload: JsonValue) -> bool:
    """Return whether the payload carries the launch-trace top-level keys."""

    if not isinstance(payload, (str, list, dict)):
        # Preserve the bare `in` TypeError that non-container JSON scalars raised.
        raise TypeError(f"argument of type {type(payload).__name__!r} is not iterable")
    return "matrix_summaries" in payload and "traces" in payload


def parse_trace_payload(payload: JsonValue) -> LaunchTracePayload:
    """Narrow a launch-trace artifact payload into the typed summary shape."""

    obj = _object(payload, "launch-trace payload")
    parsed: LaunchTracePayload = {
        "matrix_summaries": [_parse_matrix_record(r) for r in _array(obj["matrix_summaries"])],
        "traces": _parse_traces(obj["traces"]),
    }
    if "metadata" in obj:
        parsed["metadata"] = obj["metadata"]
    return parsed


def parse_baseline_payload(payload: JsonValue) -> BaselinePayload:
    """Narrow the baseline artifact payload into the fields the drift checks read."""

    obj = _object(payload, "baseline payload")
    records = [_parse_baseline_record(r) for r in _array(obj["matrix_summaries"])]
    return {
        "matrix_summaries": {record["case_id"]: record for record in records},
        "traces": _parse_traces(obj["traces"]),
    }


def _parse_baseline_record(value: JsonValue) -> BaselineMatrixRecord:
    record = _object(value, "matrix_summaries entry")
    return {
        "case_id": _str(record["case_id"], "case_id"),
        "phase_order_observed": _str_list(record["phase_order_observed"], "phase_order_observed"),
        "strike_classification": _str(record["strike_classification"], "strike_classification"),
        "handoff_to_board_step": _int_or_none(
            record["handoff_to_board_step"], "handoff_to_board_step"
        ),
        "first_board_collision_step": _int_or_none(
            record["first_board_collision_step"], "first_board_collision_step"
        ),
        "peak_speed": _number(record["peak_speed"], "peak_speed"),
        "max_displacement_px": _number(record["max_displacement_px"], "max_displacement_px"),
    }


def _parse_matrix_record(value: JsonValue) -> MatrixSummaryRecord:
    record = _object(value, "matrix_summaries entry")
    return {
        **_parse_baseline_record(record),
        "hold_profile": _str(record["hold_profile"], "hold_profile"),
        "sw16_exit_observed": _bool(record["sw16_exit_observed"], "sw16_exit_observed"),
        "min_vy": _number(record["min_vy"], "min_vy"),
        "invariant_violations": _str_list(record["invariant_violations"], "invariant_violations"),
    }


def _parse_traces(value: JsonValue) -> dict[str, list[TraceStep]]:
    traces = _object(value, "traces")
    return {
        case_id: [_parse_trace_step(step) for step in _array(steps)]
        for case_id, steps in traces.items()
    }


def _parse_trace_step(value: JsonValue) -> TraceStep:
    step = _object(value, "trace step entry")
    return {
        "step_index": _int(step["step_index"], "step_index"),
        "phase": _str(step["phase"], "phase"),
        "seam_transition": step["seam_transition"],
        "handoff_to_board_step": _int_or_none(
            step["handoff_to_board_step"], "handoff_to_board_step"
        ),
        "first_board_collision_step": _int_or_none(
            step["first_board_collision_step"], "first_board_collision_step"
        ),
    }


def _object(value: JsonValue, what: str) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise TypeError(f"{what} is not a JSON object: {type(value).__name__}")
    return value


def _array(value: JsonValue) -> list[JsonValue]:
    if not isinstance(value, list):
        raise TypeError(f"expected a JSON array: {type(value).__name__}")
    return value


def _str(value: JsonValue, field: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} is not a string: {type(value).__name__}")
    return value


def _bool(value: JsonValue, field: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{field} is not a boolean: {type(value).__name__}")
    return value


def _int(value: JsonValue, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field} is not an integer: {type(value).__name__}")
    return value


def _int_or_none(value: JsonValue, field: str) -> int | None:
    return None if value is None else _int(value, field)


def _number(value: JsonValue, field: str) -> Number:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError(f"{field} is not a number: {type(value).__name__}")
    return value


def _str_list(value: JsonValue, field: str) -> list[str]:
    return [_str(item, field) for item in _array(value)]
