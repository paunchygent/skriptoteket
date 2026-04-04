"""Unit tests for Flunk-Out Frenzy launch-trace operational summaries.

Purpose:
    Lock the PR-0214 operator surface so launch-trace summaries remain
    deterministic, baseline-aware, and traceable back to raw rows.
Relationships:
    - Exercises `scripts._flunk_out_frenzy_launch_trace_summary`
    - Verifies case/run verdicts, spotlight-row derivation, and baseline gates
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import _flunk_out_frenzy_launch_trace_summary as module


def _make_trace_payload(
    *, handoff_step: int = 149, strike_classification: str = "strike_and_route_accepted"
) -> dict:
    steps = [
        {
            "step_index": 1,
            "dt_ms": 16,
            "phase": "charge_pull",
            "ball_owner": "launcher_chain",
            "ball_position": None,
            "ball_velocity": None,
            "plunger": {},
            "route": {},
            "route_capture": {},
            "sensors": {},
            "contact": {},
            "seam_transition": None,
            "events": [],
            "handoff_to_board_step": None,
            "first_board_collision_step": None,
            "board_collision_started_this_step": False,
        },
        {
            "step_index": 2,
            "dt_ms": 16,
            "phase": "route_endpoint_bridge",
            "ball_owner": "launcher_chain",
            "ball_position": None,
            "ball_velocity": None,
            "plunger": {},
            "route": {},
            "route_capture": {},
            "sensors": {},
            "contact": {},
            "seam_transition": {
                "fromRouteTag": "launcher/travel/overhead",
                "toRouteTag": "launcher/travel/endpoint-bridge",
                "xyDeltaPx": 0,
                "zDeltaPx": 0,
            },
            "events": [],
            "handoff_to_board_step": None,
            "first_board_collision_step": None,
            "board_collision_started_this_step": False,
        },
        {
            "step_index": 3,
            "dt_ms": 16,
            "phase": "route_descent",
            "ball_owner": "launcher_chain",
            "ball_position": None,
            "ball_velocity": None,
            "plunger": {},
            "route": {},
            "route_capture": {},
            "sensors": {},
            "contact": {},
            "seam_transition": {
                "fromRouteTag": "launcher/travel/endpoint-bridge",
                "toRouteTag": "launcher/travel/descent",
                "xyDeltaPx": 0,
                "zDeltaPx": 0,
            },
            "events": [],
            "handoff_to_board_step": None,
            "first_board_collision_step": None,
            "board_collision_started_this_step": False,
        },
        {
            "step_index": handoff_step,
            "dt_ms": 16,
            "phase": "handoff_to_board",
            "ball_owner": "main_world",
            "ball_position": None,
            "ball_velocity": None,
            "plunger": {},
            "route": {},
            "route_capture": {},
            "sensors": {},
            "contact": {},
            "seam_transition": None,
            "events": [],
            "handoff_to_board_step": handoff_step,
            "first_board_collision_step": None,
            "board_collision_started_this_step": False,
        },
        {
            "step_index": handoff_step + 1,
            "dt_ms": 16,
            "phase": "board_drop_preimpact",
            "ball_owner": "main_world",
            "ball_position": None,
            "ball_velocity": None,
            "plunger": {},
            "route": {},
            "route_capture": {},
            "sensors": {},
            "contact": {},
            "seam_transition": None,
            "events": [],
            "handoff_to_board_step": handoff_step,
            "first_board_collision_step": handoff_step + 1,
            "board_collision_started_this_step": True,
        },
    ]
    return {
        "metadata": {
            "generated_at_utc": "2026-04-04T09:33:48.287Z",
            "repo_branch": "local",
            "engine_version_marker": "pr-0209-launch-to-drop-trace",
        },
        "matrix_summaries": [
            {
                "case_id": "K-MEDIUM-STEADY",
                "hold_profile": "medium",
                "dt_ms": 16,
                "hold_steps": 26,
                "relaunch_gap_steps": 16,
                "observation_steps": 60,
                "board_drop_observation_steps": 300,
                "phase_order_observed": [
                    "charge_pull",
                    "route_endpoint_bridge",
                    "route_descent",
                    "handoff_to_board",
                    "board_drop_preimpact",
                ],
                "sw16_exit_observed": True,
                "handoff_to_board_step": handoff_step,
                "first_board_collision_step": handoff_step + 1,
                "peak_speed": 1759.3111658253963,
                "min_vy": -1759.3111572265625,
                "max_displacement_px": 1086.2518681524157,
                "strike_classification": strike_classification,
                "invariant_violations": [],
            }
        ],
        "traces": {
            "K-MEDIUM-STEADY": steps,
        },
    }


def _write_payload(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")
    return path


def test_build_trace_summary_passes_with_matching_baseline(tmp_path: Path) -> None:
    raw_payload = _make_trace_payload()
    baseline_path = _write_payload(tmp_path / "baseline.json", _make_trace_payload())

    summary = module.build_trace_summary(
        raw_payload,
        raw_artifact_path=tmp_path / "raw.json",
        baseline_artifact_path=baseline_path,
    )
    artifacts = module.write_trace_summary_artifacts(
        tmp_path,
        raw_artifact_path=tmp_path / "raw.json",
        summary_payload=summary,
    )

    assert summary["run_summary"]["run_verdict"] == module.RUN_PASS
    assert summary["case_summaries"][0]["case_verdict"] == module.CASE_PASS
    assert any(
        row["phase"] == "route_endpoint_bridge" and "seam_transition" in row["reasons"]
        for row in summary["case_summaries"][0]["spotlight_rows"]
    )
    assert artifacts.summary_json_path.is_file()
    assert artifacts.summary_markdown_path.is_file()
    assert "Run verdict: `pass`" in artifacts.summary_markdown_path.read_text(encoding="utf-8")


def test_build_trace_summary_blocks_when_baseline_is_missing(tmp_path: Path) -> None:
    raw_payload = _make_trace_payload()
    summary = module.build_trace_summary(
        raw_payload,
        raw_artifact_path=tmp_path / "raw.json",
        baseline_artifact_path=tmp_path / "missing-baseline.json",
    )

    assert summary["run_summary"]["run_verdict"] == module.RUN_BLOCKED
    assert summary["case_summaries"][0]["case_verdict"] == module.CASE_BLOCKED
    assert "baseline_unavailable:missing" in summary["case_summaries"][0]["case_blockers"]
    with pytest.raises(AssertionError, match="decision gate blocked"):
        module.fail_if_summary_gate_blocked(summary)


def test_build_trace_summary_blocks_when_baseline_is_unreadable(tmp_path: Path) -> None:
    raw_payload = _make_trace_payload()
    unreadable_path = tmp_path / "baseline.json"
    unreadable_path.write_text("{not-json}\n", encoding="utf-8")

    summary = module.build_trace_summary(
        raw_payload,
        raw_artifact_path=tmp_path / "raw.json",
        baseline_artifact_path=unreadable_path,
    )

    assert summary["run_summary"]["baseline_status"] == module.BASELINE_UNREADABLE
    assert summary["run_summary"]["run_verdict"] == module.RUN_BLOCKED


def test_build_trace_summary_flags_attention_for_step_drift_with_baseline(tmp_path: Path) -> None:
    raw_payload = _make_trace_payload(handoff_step=152)
    baseline_path = _write_payload(
        tmp_path / "baseline.json", _make_trace_payload(handoff_step=149)
    )

    summary = module.build_trace_summary(
        raw_payload,
        raw_artifact_path=tmp_path / "raw.json",
        baseline_artifact_path=baseline_path,
    )

    assert summary["run_summary"]["run_verdict"] == module.RUN_PASS_WITH_RESERVATIONS
    assert summary["case_summaries"][0]["case_verdict"] == module.CASE_ATTENTION
    assert (
        "handoff_to_board_step_drift_attention" in summary["case_summaries"][0]["case_attentions"]
    )
