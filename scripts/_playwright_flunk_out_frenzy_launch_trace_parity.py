"""Focused Playwright collector for Flunk-Out Frenzy launch-trace parity.

This child module keeps the PR-0213 browser proof intentionally narrow: log in,
start the runtime, ask the DEV debug seam for the canonical launch-to-drop
artifact payload, persist it, and fail if any invariant violations remain.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from playwright.sync_api import Page, sync_playwright

from scripts._flunk_out_frenzy_launch_trace_summary import (
    DEFAULT_BASELINE_ARTIFACT_PATH,
    LaunchTraceSummaryArtifacts,
    build_trace_summary,
    fail_if_summary_gate_blocked,
    write_trace_summary_artifacts,
)
from scripts._playwright_browser import launch_chromium
from scripts._playwright_config import get_config
from scripts._playwright_flunk_out_frenzy import (
    login_to_flunk_out_frenzy,
    verify_runtime_start,
    wait_for_debug_handle,
)

DEFAULT_ARTIFACT_DIR = Path(".artifacts/flunk-out-frenzy-launch-to-drop")
DEBUG_EVALUATE_TIMEOUT_MS = 60_000


def parse_args(argv: Sequence[str] | None = None) -> tuple[argparse.Namespace, list[str]]:
    """Parse script-specific args and return the remaining shared config args."""

    parser = argparse.ArgumentParser(
        description="Run focused Flunk-Out Frenzy launch-trace parity proof."
    )
    parser.add_argument(
        "--artifact-dir",
        default=str(DEFAULT_ARTIFACT_DIR),
        help="Directory for JSON artifacts.",
    )
    parser.add_argument(
        "--baseline-artifact",
        default=str(DEFAULT_BASELINE_ARTIFACT_PATH),
        help="Pinned baseline artifact for PR-0214 drift checks.",
    )
    return parser.parse_known_args(argv)


def collect_trace_payload(page: Page) -> dict[str, Any]:
    """Collect the canonical launch-trace artifact payload from the browser."""

    return page.evaluate(
        """async () => {
          return window.__FOF_DEBUG__.buildLaunchToDropTraceArtifact();
        }"""
    )


def write_artifact(artifact_dir: Path, payload: dict[str, Any]) -> Path:
    """Persist the collected launch-trace artifact payload and return the file path."""

    artifact_dir.mkdir(parents=True, exist_ok=True)
    output_path = artifact_dir / "launch-to-drop-trace-matrix.json"
    output_path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")
    return output_path


def fail_if_matrix_invariants_red(payload: dict[str, Any]) -> None:
    """Raise when any canonical launch-trace matrix invariant is violated."""

    failing = [
        record
        for record in payload.get("matrix_summaries", [])
        if record.get("invariant_violations")
    ]
    if not failing:
        return
    details = "; ".join(
        f"{record['case_id']}: {', '.join(record['invariant_violations'])}" for record in failing
    )
    raise AssertionError(f"PR-0213 launch trace parity invariant failures -> {details}")


def run(argv: Sequence[str] | None = None) -> LaunchTraceSummaryArtifacts:
    """Run the focused browser-side launch-trace parity proof."""

    args, remaining_config_argv = parse_args(argv)
    config = get_config(argv=remaining_config_argv)
    artifact_dir = Path(args.artifact_dir)
    baseline_artifact_path = Path(args.baseline_artifact)
    base_url = config.base_url.rstrip("/")
    raw_artifact_path = artifact_dir / "launch-to-drop-trace-matrix.json"

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(viewport={"width": 1600, "height": 1200})
        page = context.new_page()
        page.set_default_timeout(DEBUG_EVALUATE_TIMEOUT_MS)

        login_to_flunk_out_frenzy(
            page,
            base_url=base_url,
            email=config.email,
            password=config.password,
        )
        verify_runtime_start(page)
        wait_for_debug_handle(page)

        payload = collect_trace_payload(page)
        write_artifact(artifact_dir, payload)
        fail_if_matrix_invariants_red(payload)
        summary_payload = build_trace_summary(
            payload,
            raw_artifact_path=raw_artifact_path,
            baseline_artifact_path=baseline_artifact_path,
            baseline_override_used=baseline_artifact_path != DEFAULT_BASELINE_ARTIFACT_PATH,
        )
        artifact_paths = write_trace_summary_artifacts(
            artifact_dir,
            raw_artifact_path=raw_artifact_path,
            summary_payload=summary_payload,
        )
        fail_if_summary_gate_blocked(summary_payload)
        page.screenshot(path=str(artifact_dir / "launch-to-drop-proof.png"), full_page=True)

        context.close()
        browser.close()

    return artifact_paths
