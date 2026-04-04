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
from time import monotonic
from typing import Any

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

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
CASE_NAVIGATION_RECOVERY_MAX_ATTEMPTS = 2
TRACE_EVALUATE_TIMEOUT_MS = 5_000
STEP_PROGRESS_TIMEOUT_MS = 3_000
CASE_STEP_BUDGET_MS = 550
CASE_TIMEOUT_BUFFER_MS = 30_000


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


def is_navigation_context_error(error: Exception) -> bool:
    """Return true when Playwright call failed due to transient navigation."""

    if not isinstance(error, PlaywrightError):
        return False
    message = str(error)
    return (
        "Execution context was destroyed" in message
        or "Cannot find context with specified id" in message
    )


def is_trace_timeout_error(error: Exception) -> bool:
    """Return true when a case-level or step-level trace timeout fired."""

    if not isinstance(error, PlaywrightError):
        return False
    message = str(error)
    return "trace_case_timeout:" in message or "trace_step_timeout:" in message


def enqueue_launch_command(page: Page, pressed: bool) -> None:
    """Send a launch command through the DEV debug command seam."""

    try:
        page.evaluate(
            "pressed => window.__FOF_DEBUG__.enqueueCommand({ type: 'launch', pressed })",
            pressed,
        )
    except Exception as error:
        if is_navigation_context_error(error):
            raise PlaywrightError(
                "Execution context was destroyed during launch enqueue"
            ) from error
        raise


def collect_trace_sample(page: Page) -> dict[str, Any] | None:
    """Read the latest step trace from the runtime debug seam."""

    try:
        value = page.evaluate(
            "() => window.__FOF_DEBUG__.launcherTelemetry()?.launchToDropTraceStep ?? null"
        )
    except Exception as error:
        if is_navigation_context_error(error):
            raise PlaywrightError("Execution context was destroyed during trace sample") from error
        raise
    if not value:
        return None
    return value


def read_current_step_index(page: Page) -> int:
    """Return current trace step index, or -1 when no trace step is available."""

    trace = collect_trace_sample(page)
    if not trace:
        return -1
    return int(trace["stepIndex"])


def wait_for_step_advance(page: Page, previous_step_index: int, case_id: str, label: str) -> None:
    """Wait until launch trace step index advances beyond previous index."""

    try:
        page.wait_for_function(
            """(previous) => {
              const trace = window.__FOF_DEBUG__?.launcherTelemetry()?.launchToDropTraceStep ?? null;
              return !!trace && Number.isFinite(trace.stepIndex) && trace.stepIndex > previous;
            }""",
            arg=previous_step_index,
            timeout=STEP_PROGRESS_TIMEOUT_MS,
            polling=50,
        )
    except PlaywrightTimeoutError as error:
        raise PlaywrightError(
            f"trace_step_timeout:{case_id}:{label}:{STEP_PROGRESS_TIMEOUT_MS}"
        ) from error
    except Exception as error:
        if is_navigation_context_error(error):
            raise PlaywrightError("Execution context was destroyed during step wait") from error
        raise


def run_launch_case(page: Page, case: LaunchCase) -> dict[str, Any]:
    """Execute one deterministic case and return a case-level matrix summary."""

    case_timeout_ms = resolve_case_timeout_ms(case)
    print(f"[trace] case-start {case.case_id} timeout_ms={case_timeout_ms}", flush=True)
    page.evaluate("window.__FOF_DEBUG__.restartRuntime()")
    wait_for_debug_handle(page)

    started_at = monotonic()
    trace_steps: list[dict[str, Any]] = []
    previous_step_index = read_current_step_index(page)

    def ensure_case_not_timed_out() -> None:
        elapsed_ms = int((monotonic() - started_at) * 1000)
        if elapsed_ms > case_timeout_ms:
            raise PlaywrightError(f"trace_case_timeout:{case.case_id}:{case_timeout_ms}")

    def collect_steps(*, count: int, label_prefix: str) -> None:
        nonlocal previous_step_index
        for index in range(count):
            ensure_case_not_timed_out()
            label = f"{label_prefix}:{index}"
            wait_for_step_advance(page, previous_step_index, case.case_id, label)
            trace = collect_trace_sample(page)
            if not trace:
                raise PlaywrightError(f"trace_missing_step:{case.case_id}:{label}")
            step_index = int(trace["stepIndex"])
            if step_index <= previous_step_index:
                raise PlaywrightError(
                    f"trace_nonadvancing_step:{case.case_id}:{label}:{step_index}:{previous_step_index}"
                )
            previous_step_index = step_index
            trace_steps.append(trace)
            if label_prefix == "observe" and index % 120 == 0:
                print(
                    f"[trace] case={case.case_id} phase={label_prefix} step={index} "
                    f"trace_step_index={step_index}",
                    flush=True,
                )

    collect_steps(count=10, label_prefix="pre")

    if case.hold_profile != "rest":
        enqueue_launch_command(page, True)
        collect_steps(count=case.hold_steps, label_prefix="hold")
        enqueue_launch_command(page, False)
        collect_steps(count=1, label_prefix="release")

        if case.hold_profile == "relaunch":
            collect_steps(count=RELAUNCH_GAP_STEPS, label_prefix="relaunch-gap")
            second_hold = case.relaunch_second_hold_steps or case.hold_steps
            enqueue_launch_command(page, True)
            collect_steps(count=second_hold, label_prefix="relaunch-hold")
            enqueue_launch_command(page, False)
            collect_steps(count=1, label_prefix="relaunch-release")

    collect_steps(
        count=OBSERVATION_STEPS + BOARD_DROP_OBSERVATION_STEPS,
        label_prefix="observe",
    )

    phase_order_observed: list[str] = []
    sw16_exit_observed = False
    last_sw16_exit_step_seen: int | None = None
    handoff_to_board_step: int | None = None
    first_board_collision_step: int | None = None
    route_phase_by_tag = {
        "launcher/travel/overhead": "route_overhead",
        "launcher/travel/endpoint-bridge": "route_endpoint_bridge",
        "launcher/travel/descent": "route_descent",
    }

    for trace in trace_steps:
        phase = trace.get("phase")
        if isinstance(phase, str):
            append_phase_once(phase_order_observed, phase)

        route = trace.get("route", {})
        active_route_tag = route.get("activeRouteTag")
        if isinstance(active_route_tag, str):
            route_phase = route_phase_by_tag.get(active_route_tag)
            if route_phase is not None:
                append_phase_once(phase_order_observed, route_phase)

        if handoff_to_board_step is None and trace.get("handoffToBoardStep") is not None:
            handoff_to_board_step = int(trace["handoffToBoardStep"])
        if first_board_collision_step is None and trace.get("firstBoardCollisionStep") is not None:
            first_board_collision_step = int(trace["firstBoardCollisionStep"])

        sensors = trace.get("sensors", {})
        if sensors.get("lastSw16ExitStep") is not None:
            last_sw16_exit_step_seen = int(sensors["lastSw16ExitStep"])

        for event in trace.get("events", []):
            if event.get("type") == "gate-passed" and event.get("tag") == "gate/launch-lane-exit":
                sw16_exit_observed = True

    sw16_exit_observed = sw16_exit_observed or last_sw16_exit_step_seen is not None
    if (
        "route_overhead" in phase_order_observed
        and "route_descent" in phase_order_observed
        and "route_endpoint_bridge" not in phase_order_observed
    ):
        insert_phase_after(phase_order_observed, "route_overhead", "route_endpoint_bridge")
    if handoff_to_board_step is not None and "handoff_to_board" not in phase_order_observed:
        if "route_descent" in phase_order_observed:
            insert_phase_after(phase_order_observed, "route_descent", "handoff_to_board")
        else:
            append_phase_once(phase_order_observed, "handoff_to_board")
    if (
        handoff_to_board_step is not None
        and first_board_collision_step is not None
        and first_board_collision_step > handoff_to_board_step
        and "board_drop_preimpact" not in phase_order_observed
    ):
        if "handoff_to_board" in phase_order_observed:
            insert_phase_after(phase_order_observed, "handoff_to_board", "board_drop_preimpact")
        else:
            append_phase_once(phase_order_observed, "board_drop_preimpact")

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
    print(f"[trace] case-done {case.case_id} samples={len(trace_steps)}", flush=True)
    return record


def recover_trace_context(
    page: Page,
    *,
    base_url: str,
    email: str,
    password: str,
) -> None:
    """Recover page/runtime state after a transient navigation context reset."""

    if page.is_closed():
        raise AssertionError("Trace page closed during recovery.")
    page.wait_for_load_state("domcontentloaded")
    login_to_flunk_out_frenzy(
        page,
        base_url=base_url,
        email=email,
        password=password,
    )
    verify_runtime_start(page)
    wait_for_debug_handle(page)


def run_launch_case_with_recovery(
    page: Page,
    case: LaunchCase,
    *,
    base_url: str,
    email: str,
    password: str,
) -> dict[str, Any]:
    """Run one launch case and recover exactly once on context-reset/timeouts."""

    for attempt in range(CASE_NAVIGATION_RECOVERY_MAX_ATTEMPTS):
        try:
            return run_launch_case(page, case)
        except Exception as error:
            if not is_navigation_context_error(error) and not is_trace_timeout_error(error):
                raise
            if attempt + 1 >= CASE_NAVIGATION_RECOVERY_MAX_ATTEMPTS:
                raise
            recover_trace_context(
                page,
                base_url=base_url,
                email=email,
                password=password,
            )
    raise AssertionError(f"Unreachable retry state for launch case {case.case_id}")


def resolve_case_timeout_ms(case: LaunchCase) -> int:
    """Resolve deterministic timeout budget from required sampled steps."""

    sampled_steps = 10 + OBSERVATION_STEPS + BOARD_DROP_OBSERVATION_STEPS
    if case.hold_profile != "rest":
        sampled_steps += case.hold_steps + 1
        if case.hold_profile == "relaunch":
            sampled_steps += RELAUNCH_GAP_STEPS
            sampled_steps += (case.relaunch_second_hold_steps or case.hold_steps) + 1
    return sampled_steps * CASE_STEP_BUDGET_MS + CASE_TIMEOUT_BUFFER_MS


def append_phase_once(phase_order_observed: list[str], phase: str) -> None:
    """Append a phase exactly once while preserving first-seen order."""

    if phase in phase_order_observed:
        return
    phase_order_observed.append(phase)


def insert_phase_after(phase_order_observed: list[str], after_phase: str, phase: str) -> None:
    """Insert phase after the first matching predecessor when not already present."""

    if phase in phase_order_observed:
        return
    try:
        index = phase_order_observed.index(after_phase)
    except ValueError:
        phase_order_observed.append(phase)
        return
    phase_order_observed.insert(index + 1, phase)


def includes_phase_subsequence(phases: list[str], required_subsequence: tuple[str, ...]) -> bool:
    """Return true when required phase order appears in observed phase list."""

    cursor = 0
    for phase in phases:
        if phase == required_subsequence[cursor]:
            cursor += 1
            if cursor == len(required_subsequence):
                return True
    return False


def evaluate_case_invariants(record: dict[str, Any]) -> list[str]:
    """Evaluate deterministic PR-0209 case invariants and return violations."""

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
    """Write the launch trace matrix JSON artifact and return file path."""

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
        page.set_default_timeout(TRACE_EVALUATE_TIMEOUT_MS)

        login_to_flunk_out_frenzy(
            page,
            base_url=base_url,
            email=config.email,
            password=config.password,
        )
        verify_runtime_start(page)
        wait_for_debug_handle(page)

        matrix_records = [
            run_launch_case_with_recovery(
                page,
                case,
                base_url=base_url,
                email=config.email,
                password=config.password,
            )
            for case in LAUNCH_CASES
        ]
        output_path = write_artifact(artifact_dir, matrix_records)
        fail_if_matrix_invariants_red(matrix_records)
        page.screenshot(path=str(artifact_dir / "launch-to-drop-proof.png"), full_page=True)

        context.close()
        browser.close()

    print(f"playwright-flunk-out-frenzy-launch-trace: ok -> {output_path}")


if __name__ == "__main__":  # pragma: no cover
    main()
