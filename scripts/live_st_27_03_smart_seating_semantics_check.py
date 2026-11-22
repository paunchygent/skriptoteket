"""Live smart-seating semantics proof for G20 / SA24D.

This script runs against the local live backend and validates the solver with
the real `G20` room geometry plus the `SA24D` rule set from the agreed
screenshots:

- 6-student `Keep apart` cluster
- 2-student `Keep near` cluster
- 2-student `Närmare läraren` preferences
- export-backed history enabled

It creates real seating export checkpoints through the app, then simulates
hundreds of backend smart runs and asserts the same invariants as the domain
scenario suite while writing a JSON summary artifact.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from statistics import mean
from urllib.parse import urlparse
from uuid import uuid4

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from scripts._playwright_huleedu_auth import create_signed_huleedu_api_session  # noqa: E402
from scripts._smart_seating_semantics_api import (  # noqa: E402
    create_export_checkpoint,
    create_roster,
    create_seating_draft,
    get_g20_template,
    patch_draft,
    patch_smart_rules,
    run_smart_seating,
)
from scripts._smart_seating_semantics_support import (  # noqa: E402
    KEEP_NEAR_STUDENT_IDS,
    MIN_NEAR_TEACHER_DISTINCT_SEAT_COUNT,
    MIN_NEAR_TEACHER_ROTATION_POOL_SIZE,
    NEAR_TEACHER_STUDENT_IDS,
    RunSummary,
    build_topology,
    near_teacher_pool_seat_ids,
    rotated_assignments,
    validate_workspace,
)

ARTIFACTS_DIR = REPO_ROOT / ".artifacts" / "st-27-03-smart-seating-semantics"
DEFAULT_RUN_COUNT = 120
_HISTORY_CHECKPOINT_COUNT = 6
MIN_VALID_LAYOUT_COUNT = 10
MIN_DISTINCT_SEAT_COUNT = 2


def _api_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme and parsed.hostname and parsed.port == 5173:
        return f"{parsed.scheme}://{parsed.hostname}:8000"
    return base_url.rstrip("/")


def _read_bootstrap_email() -> str:
    env_path = REPO_ROOT / ".env"
    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"')
    return values["BOOTSTRAP_SUPERUSER_EMAIL"]


def _create_api_session(*, api_base_url: str, email: str) -> tuple[requests.Session, str]:
    auth = create_signed_huleedu_api_session(
        email=email,
        display_name="ST 27-03 Smart Seating Teacher",
        jti="st-27-03-smart-seating",
    )
    return auth.api_session, "huleedu-gateway-context"


def main() -> None:
    parser = argparse.ArgumentParser(description="Live G20 / SA24D smart-seating semantics proof")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:5173",
        help="App base URL (default: http://127.0.0.1:5173)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=DEFAULT_RUN_COUNT,
        help=f"Number of live smart reruns to simulate (default: {DEFAULT_RUN_COUNT})",
    )
    args = parser.parse_args()

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    api_base_url = _api_base_url(args.base_url)
    email = _read_bootstrap_email()
    session, csrf_token = _create_api_session(
        api_base_url=api_base_url,
        email=email,
    )

    template = get_g20_template(session, api_base_url=api_base_url)
    topology = build_topology(template)
    run_name_suffix = uuid4().hex[:6]
    roster = create_roster(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        name=f"ST27-03 Semantics {run_name_suffix}",
    )
    draft = create_seating_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=roster["id"],
        template_id=template["id"],
    )
    draft_id = draft["id"]
    patch_smart_rules(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        roster_id=roster["id"],
        expected_revision=0,
    )

    revision = draft["revision"]
    for offset in range(_HISTORY_CHECKPOINT_COUNT):
        revision = patch_draft(
            session,
            api_base_url=api_base_url,
            csrf_token=csrf_token,
            draft_id=draft_id,
            expected_revision=revision,
            smart_enabled=True,
            use_history=True,
            seat_assignments=rotated_assignments(template, offset),
        )
        create_export_checkpoint(
            session,
            api_base_url=api_base_url,
            csrf_token=csrf_token,
            draft_id=draft_id,
        )

    revision = patch_draft(
        session,
        api_base_url=api_base_url,
        csrf_token=csrf_token,
        draft_id=draft_id,
        expected_revision=revision,
        smart_enabled=True,
        use_history=True,
        seat_assignments=[],
    )

    samples: list[RunSummary] = []
    for _ in range(args.runs):
        result = run_smart_seating(
            session,
            api_base_url=api_base_url,
            csrf_token=csrf_token,
            draft_id=draft_id,
            expected_revision=revision,
        )
        if result["status"] != "applied":
            raise AssertionError(f"Unexpected smart-run status: {result}")
        if result["used_history"] is not True:
            raise AssertionError("Live smart run did not use history.")
        if result["message"] != "Smart placering klar med stöd av tidigare exporter.":
            raise AssertionError(f"Unexpected live smart-run message: {result['message']}")
        workspace = result["workspace"]
        revision = workspace["draft"]["revision"]
        samples.append(validate_workspace(workspace=workspace, topology=topology))

    unique_layout_count = len({sample.layout_signature for sample in samples})
    if unique_layout_count < MIN_VALID_LAYOUT_COUNT:
        raise AssertionError(
            f"Expected at least {MIN_VALID_LAYOUT_COUNT} valid live layouts, got {unique_layout_count}."
        )
    distinct_seat_counts = {
        student_id: len({sample.assignments_by_student[student_id] for sample in samples})
        for student_id in samples[0].assignments_by_student
    }
    if min(distinct_seat_counts.values()) < MIN_DISTINCT_SEAT_COUNT:
        raise AssertionError("At least one student failed to rotate across live smart reruns.")
    teacher_pool_seat_ids = near_teacher_pool_seat_ids(topology)
    occupied_near_teacher_pool_seat_ids = {
        sample.assignments_by_student[student_id]
        for sample in samples
        for student_id in NEAR_TEACHER_STUDENT_IDS
    }
    near_teacher_distinct_seat_counts = {
        student_id: len({sample.assignments_by_student[student_id] for sample in samples})
        for student_id in NEAR_TEACHER_STUDENT_IDS
    }
    if min(near_teacher_distinct_seat_counts.values()) < MIN_NEAR_TEACHER_DISTINCT_SEAT_COUNT:
        raise AssertionError("Near-teacher students failed to rotate across a broad valid pool.")
    if not occupied_near_teacher_pool_seat_ids <= teacher_pool_seat_ids:
        raise AssertionError("Near-teacher students left the valid rotating teacher pool.")
    if len(occupied_near_teacher_pool_seat_ids) < MIN_NEAR_TEACHER_ROTATION_POOL_SIZE:
        raise AssertionError("Near-teacher pool coverage did not rotate across a broad valid pool.")
    keep_near_modes = {
        topology.pair(
            sample.assignments_by_student[KEEP_NEAR_STUDENT_IDS[0]],
            sample.assignments_by_student[KEEP_NEAR_STUDENT_IDS[1]],
        ).keep_near_relation_mode
        for sample in samples
    }
    keep_near_modes.discard(None)
    if len(keep_near_modes) < 3:
        raise AssertionError(
            "Keep-near pair failed to rotate across multiple local relation modes."
        )

    summary = {
        "runs": args.runs,
        "roster_name": roster["name"],
        "draft_id": draft_id,
        "unique_layout_count": unique_layout_count,
        "min_distinct_seat_count": min(distinct_seat_counts.values()),
        "near_teacher_distinct_seat_counts": near_teacher_distinct_seat_counts,
        "min_keep_apart_block_count": min(sample.keep_apart_block_count for sample in samples),
        "mean_keep_apart_mean_distance": mean(
            sample.keep_apart_mean_distance for sample in samples
        ),
        "min_keep_apart_mean_distance": min(sample.keep_apart_mean_distance for sample in samples),
        "final_revision": revision,
        "near_teacher_pool_seat_ids": sorted(teacher_pool_seat_ids),
        "occupied_near_teacher_pool_seat_ids": sorted(occupied_near_teacher_pool_seat_ids),
        "keep_near_modes": sorted(keep_near_modes),
        "history_checkpoints_created": _HISTORY_CHECKPOINT_COUNT,
        "sample_layouts": [asdict(sample) for sample in samples[:5]],
    }
    summary_path = ARTIFACTS_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps({"status": "ok", "summary_path": str(summary_path), **summary}, indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()
