"""Run the first smart-grouping compactness simulation sweep.

Purpose:
    Produce the first operator-facing smart-grouping compactness artifacts for
    `ST-27-04` by comparing a no-classroom baseline against several quadratic
    falloff candidates on the same whole-class seating maps.

Relationships:
    - consumes `scripts._smart_grouping_compactness_support`
    - writes JSON and PNG artifacts under `.artifacts/`
    - keeps simulation/tuning evidence outside the product runtime
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts._smart_grouping_compactness_support import (  # noqa: E402
    candidate_report_payload,
    default_candidate_specs,
    load_canonical_scenarios,
    render_seating_projection,
    run_candidate,
    with_artifact_path,
)

ARTIFACTS_DIR = REPO_ROOT / ".artifacts" / "st-27-04-smart-grouping-compactness-simulations"


def main() -> None:
    """Run the first compactness sweep and write JSON/PNG artifacts."""

    scenarios = load_canonical_scenarios()
    summary_payload: dict[str, object] = {
        "scenario_count": len(scenarios),
        "candidate_count": len(default_candidate_specs()),
        "scenarios": [],
    }
    for scenario in scenarios:
        scenario_dir = ARTIFACTS_DIR / scenario.key
        scenario_dir.mkdir(parents=True, exist_ok=True)
        for existing_png in scenario_dir.glob("*.png"):
            existing_png.unlink()
        scenario_payload = {
            "key": scenario.key,
            "label": scenario.label,
            "seating_assignments_by_student": scenario.seating_assignments_by_student,
            "candidates": [],
        }
        for candidate in default_candidate_specs():
            report = run_candidate(scenario=scenario, candidate=candidate)
            artifact_path = scenario_dir / f"{candidate.key}.png"
            render_seating_projection(
                scenario=scenario,
                candidate_report=report,
                output_path=artifact_path,
            )
            scenario_payload["candidates"].append(
                candidate_report_payload(
                    with_artifact_path(
                        report=report,
                        artifact_path=str(artifact_path.relative_to(REPO_ROOT)),
                    )
                )
            )
        summary_payload["scenarios"].append(scenario_payload)

    summary_path = ARTIFACTS_DIR / "summary.json"
    summary_path.write_text(
        json.dumps(summary_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"smart-grouping-compactness-simulation: ok ({summary_path.relative_to(REPO_ROOT)})")


if __name__ == "__main__":
    main()
