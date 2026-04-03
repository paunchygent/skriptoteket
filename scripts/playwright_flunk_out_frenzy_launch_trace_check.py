"""Live launch-to-drop telemetry proof for Flunk-Out Frenzy.

This script logs in through the protected curated-app route, starts the runtime,
runs the fixed PR-0206 hold/release matrix through the DEV debug seam, captures
PR-0209 step traces, and writes a machine-readable matrix artifact.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, sync_playwright

from scripts._playwright_browser import launch_chromium
from scripts._playwright_config import get_config
from scripts._playwright_flunk_out_frenzy import (
    login_to_flunk_out_frenzy,
    verify_runtime_start,
    wait_for_debug_handle,
)

DEFAULT_ARTIFACT_DIR = Path(".artifacts/flunk-out-frenzy-launch-to-drop")
DT_MS = 16
OBSERVATION_STEPS = 60
BOARD_DROP_OBSERVATION_STEPS = 300
RELAUNCH_GAP_STEPS = 16


@dataclass(frozen=True)
class LaunchCase:
    case_id: str
    hold_profile: str
    hold_steps: int
    relaunch_second_hold_steps: int | None = None


LAUNCH_CASES: tuple[LaunchCase, ...] = (
    LaunchCase(case_id="K-REST-STEADY", hold_profile="rest", hold_steps=0),
    LaunchCase(case_id="K-SHORT-STEADY", hold_profile="short", hold_steps=8),
    LaunchCase(case_id="K-MEDIUM-STEADY", hold_profile="medium", hold_steps=26),
    LaunchCase(case_id="K-FULL-STEADY", hold_profile="full", hold_steps=56),
    LaunchCase(
        case_id="K-RELAUNCH-MEDIUM",
        hold_profile="relaunch",
        hold_steps=26,
        relaunch_second_hold_steps=26,
    ),
)

QUALIFYING_CASE_IDS: frozenset[str] = frozenset(
    {"K-MEDIUM-STEADY", "K-FULL-STEADY", "K-RELAUNCH-MEDIUM"}
)
REQUIRED_QUALIFYING_PHASE_CHAIN: tuple[str, ...] = (
    "route_overhead",
    "route_endpoint_bridge",
    "route_descent",
    "handoff_to_board",
    "board_drop_preimpact",
)


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    """Parse script-specific args and return remaining args for shared config."""

    parser = argparse.ArgumentParser(description="Run Flunk-Out Frenzy launch trace live proof.")
    parser.add_argument(
        "--artifact-dir",
        default=str(DEFAULT_ARTIFACT_DIR),
        help="Directory for JSON artifacts.",
    )
    args, remaining = parser.parse_known_args(sys.argv[1:])
    return args, remaining


def enqueue_launch_command(page: Page, pressed: bool) -> None:
    """Send a launch command through the DEV debug command seam."""

    page.evaluate(
        "pressed => window.__FOF_DEBUG__.enqueueCommand({ type: 'launch', pressed })",
        pressed,
    )


def collect_trace_sample(page: Page) -> dict[str, Any] | None:
    """Read the latest step trace from the runtime debug seam."""

    value = page.evaluate(
        "() => window.__FOF_DEBUG__.launcherTelemetry()?.launchToDropTraceStep ?? null"
    )
    if not value:
        return None
    return value


def collect_unique_trace(page: Page, samples: list[dict[str, Any]]) -> None:
    """Append the current trace sample if it has a new step index."""

    trace = collect_trace_sample(page)
    if not trace:
        return
    if samples and trace["stepIndex"] == samples[-1]["stepIndex"]:
        return
    samples.append(trace)


def run_launch_case(page: Page, case: LaunchCase) -> dict[str, Any]:
    """Execute one deterministic case and return a case-level matrix summary."""

    page.evaluate("window.__FOF_DEBUG__.restartRuntime()")
    page.wait_for_timeout(200)

    trace_steps: list[dict[str, Any]] = []

    for _ in range(10):
        enqueue_launch_command(page, False)
        page.wait_for_timeout(DT_MS)
        collect_unique_trace(page, trace_steps)

    if case.hold_profile != "rest":
        for _ in range(case.hold_steps):
            enqueue_launch_command(page, True)
            page.wait_for_timeout(DT_MS)
            collect_unique_trace(page, trace_steps)
        enqueue_launch_command(page, False)
        page.wait_for_timeout(DT_MS)
        collect_unique_trace(page, trace_steps)

        if case.hold_profile == "relaunch":
            for _ in range(RELAUNCH_GAP_STEPS):
                enqueue_launch_command(page, False)
                page.wait_for_timeout(DT_MS)
                collect_unique_trace(page, trace_steps)
            second_hold = case.relaunch_second_hold_steps or case.hold_steps
            for _ in range(second_hold):
                enqueue_launch_command(page, True)
                page.wait_for_timeout(DT_MS)
                collect_unique_trace(page, trace_steps)
            enqueue_launch_command(page, False)
            page.wait_for_timeout(DT_MS)
            collect_unique_trace(page, trace_steps)

    for _ in range(OBSERVATION_STEPS + BOARD_DROP_OBSERVATION_STEPS):
        enqueue_launch_command(page, False)
        page.wait_for_timeout(DT_MS)
        collect_unique_trace(page, trace_steps)

    phase_order_observed: list[str] = []
    sw16_exit_observed = False
    handoff_to_board_step: int | None = None
    first_board_collision_step: int | None = None

    for trace in trace_steps:
        phase = trace.get("phase")
        if phase not in phase_order_observed:
            phase_order_observed.append(phase)
        if handoff_to_board_step is None and trace.get("handoffToBoardStep") is not None:
            handoff_to_board_step = int(trace["handoffToBoardStep"])
        if first_board_collision_step is None and trace.get("firstBoardCollisionStep") is not None:
            first_board_collision_step = int(trace["firstBoardCollisionStep"])
        for event in trace.get("events", []):
            if event.get("type") == "gate-passed" and event.get("tag") == "gate/launch-lane-exit":
                sw16_exit_observed = True

    record = {
        "case_id": case.case_id,
        "hold_profile": case.hold_profile,
        "dt_ms": DT_MS,
        "hold_steps": case.hold_steps,
        "relaunch_gap_steps": RELAUNCH_GAP_STEPS,
        "observation_steps": OBSERVATION_STEPS,
        "board_drop_observation_steps": BOARD_DROP_OBSERVATION_STEPS,
        "phase_order_observed": phase_order_observed,
        "sw16_exit_observed": sw16_exit_observed,
        "handoff_to_board_step": handoff_to_board_step,
        "first_board_collision_step": first_board_collision_step,
        "trace_steps": trace_steps,
    }
    record["invariant_violations"] = evaluate_case_invariants(record)
    return record


def includes_phase_subsequence(phases: list[str], required_subsequence: tuple[str, ...]) -> bool:
    """Return true when the required phase order appears in the observed phase list."""

    cursor = 0
    for phase in phases:
        if phase == required_subsequence[cursor]:
            cursor += 1
            if cursor == len(required_subsequence):
                return True
    return False


def evaluate_case_invariants(record: dict[str, Any]) -> list[str]:
    """Evaluate deterministic PR-0209 case invariants and return violation labels."""

    violations: list[str] = []
    case_id = str(record["case_id"])
    phase_order_observed = list(record["phase_order_observed"])
    sw16_exit_observed = bool(record["sw16_exit_observed"])
    handoff_to_board_step = record["handoff_to_board_step"]
    first_board_collision_step = record["first_board_collision_step"]

    if case_id in QUALIFYING_CASE_IDS:
        if not includes_phase_subsequence(phase_order_observed, REQUIRED_QUALIFYING_PHASE_CHAIN):
            violations.append("missing_required_phase_chain")
        if not sw16_exit_observed:
            violations.append("missing_sw16_exit")
        if handoff_to_board_step is None:
            violations.append("missing_handoff_to_board_step")

    if case_id == "K-FULL-STEADY" and first_board_collision_step is None:
        violations.append("missing_first_board_collision_step_for_full_case")

    if case_id == "K-REST-STEADY":
        if sw16_exit_observed:
            violations.append("rest_case_unexpected_sw16_exit")
        if handoff_to_board_step is not None:
            violations.append("rest_case_unexpected_handoff")
        if first_board_collision_step is not None:
            violations.append("rest_case_unexpected_board_collision")

    if first_board_collision_step is not None:
        if handoff_to_board_step is None:
            violations.append("board_collision_without_handoff")
        elif int(first_board_collision_step) <= int(handoff_to_board_step):
            violations.append("board_collision_not_post_handoff")

    return violations


def write_artifact(artifact_dir: Path, matrix_records: list[dict[str, Any]]) -> Path:
    """Write the launch trace matrix JSON artifact and return the file path."""

    artifact_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "repo_branch": "local",
            "engine_version_marker": "pr-0209-launch-to-drop-trace",
        },
        "matrix_summaries": [
            {key: value for key, value in record.items() if key != "trace_steps"}
            for record in matrix_records
        ],
        "traces": {record["case_id"]: record["trace_steps"] for record in matrix_records},
    }
    output_path = artifact_dir / "launch-to-drop-trace-matrix.json"
    output_path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")
    return output_path


def fail_if_matrix_invariants_red(matrix_records: list[dict[str, Any]]) -> None:
    """Raise when any PR-0209 case invariant is violated."""

    failing = [record for record in matrix_records if record.get("invariant_violations")]
    if not failing:
        return
    details = "; ".join(
        f"{record['case_id']}: {', '.join(record['invariant_violations'])}" for record in failing
    )
    raise AssertionError(f"PR-0209 launch trace matrix invariant failures -> {details}")


def main() -> None:
    """Run the live launch trace proof and persist matrix artifacts."""

    args, remaining_config_argv = parse_args()
    config = get_config(argv=remaining_config_argv)
    base_url = config.base_url.rstrip("/")
    artifact_dir = Path(args.artifact_dir)

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1600, "height": 1200})
        page = context.new_page()

        login_to_flunk_out_frenzy(
            page,
            base_url=base_url,
            email=config.email,
            password=config.password,
        )
        verify_runtime_start(page)
        wait_for_debug_handle(page)

        matrix_records = [run_launch_case(page, case) for case in LAUNCH_CASES]
        output_path = write_artifact(artifact_dir, matrix_records)
        fail_if_matrix_invariants_red(matrix_records)
        page.screenshot(path=str(artifact_dir / "launch-to-drop-proof.png"), full_page=True)

        context.close()
        browser.close()

    print(f"playwright-flunk-out-frenzy-launch-trace: ok -> {output_path}")


if __name__ == "__main__":  # pragma: no cover
    main()
