"""Guard Reagent Prep Chef hazards vs SDS shortcards alignment in CI.

Purpose:
    Fail fast when committed hazard data drifts from committed SDS shortcards.
    This keeps risk-draft hazard codes deterministic and synchronized.

Relationships:
    - Reuses `collect_alignment(...)` from
      `scripts/align_reagent_prep_chef_hazard_codes_from_shortcards.py`.
    - Reads:
      - `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/hazards.json`
      - `data/reagent_prep_chef/sds/shortcards.json`
    - Intended for quality gates (CI/pre-commit/lint composites).
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from scripts.align_reagent_prep_chef_hazard_codes_from_shortcards import collect_alignment

DEFAULT_HAZARDS_PATH = Path(
    "src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/hazards.json"
)
DEFAULT_SHORTCARDS_PATH = Path("data/reagent_prep_chef/sds/shortcards.json")


@dataclass(frozen=True, slots=True)
class GuardResult:
    """Result of evaluating hazards↔shortcards drift rules."""

    manual_validation_required: bool
    backfill_candidates: list[str]
    mismatched_non_empty: list[str]
    missing_shortcards: list[str]
    failures: list[str]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hazards-path", type=Path, default=DEFAULT_HAZARDS_PATH)
    parser.add_argument("--shortcards-path", type=Path, default=DEFAULT_SHORTCARDS_PATH)
    parser.add_argument(
        "--sample-size",
        type=int,
        default=10,
        help="How many keys to show per failing category.",
    )
    return parser.parse_args()


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_hazards(path: Path) -> list[dict[str, object]]:
    payload = _load_json(path)
    if not isinstance(payload, list):
        raise SystemExit(f"Unexpected hazards payload: {path}")
    hazards: list[dict[str, object]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise SystemExit(f"Unexpected hazards entry shape: {path}")
        hazards.append(dict(item))
    return hazards


def _load_shortcards(path: Path) -> dict[str, object]:
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise SystemExit(f"Unexpected shortcards payload: {path}")
    return payload


def _manual_validation_required(shortcards_payload: dict[str, object]) -> bool:
    manual = shortcards_payload.get("manual_validation")
    if not isinstance(manual, dict):
        return False
    required = manual.get("required")
    return bool(required) if isinstance(required, bool) else False


def evaluate_guard(
    *,
    hazards: list[dict[str, object]],
    shortcards_payload: dict[str, object],
) -> GuardResult:
    """Evaluate drift rules for hazards↔shortcards synchronization.

    Rules (all blocking):
      1) `manual_validation.required` must be false.
      2) No backfill candidates allowed (`hazard_codes=[]` while shortcard has H-codes).
      3) No non-empty mismatches allowed (`hazard_codes != shortcard_h_codes`).
      4) No hazard key may be missing in shortcards.
    """
    alignment = collect_alignment(hazards=hazards, shortcards_payload=shortcards_payload)
    manual_required = _manual_validation_required(shortcards_payload)

    failures: list[str] = []
    if manual_required:
        failures.append(
            "shortcards manual validation is required; guard blocks until shortcards are revalidated."
        )
    if alignment.backfill_by_key:
        failures.append(
            "hazards has backfill candidates from shortcards (empty H-codes in hazards)."
        )
    if alignment.mismatched_non_empty:
        failures.append("hazards and shortcards have non-empty H-code mismatches.")
    if alignment.missing_shortcards:
        failures.append("hazards entries are missing corresponding shortcards.")

    return GuardResult(
        manual_validation_required=manual_required,
        backfill_candidates=sorted(alignment.backfill_by_key.keys()),
        mismatched_non_empty=alignment.mismatched_non_empty,
        missing_shortcards=alignment.missing_shortcards,
        failures=failures,
    )


def _preview(values: list[str], *, sample_size: int) -> str:
    if not values:
        return "[]"
    sample = values[:sample_size]
    suffix = "" if len(values) <= sample_size else f" ... (+{len(values) - sample_size} more)"
    return f"{sample}{suffix}"


def main() -> None:
    args = _parse_args()
    hazards = _load_hazards(args.hazards_path)
    shortcards_payload = _load_shortcards(args.shortcards_path)

    result = evaluate_guard(hazards=hazards, shortcards_payload=shortcards_payload)

    print(
        "[hazard_shortcard_guard_summary] "
        f"manual_validation_required={result.manual_validation_required} "
        f"backfill_candidates={len(result.backfill_candidates)} "
        f"mismatched_non_empty={len(result.mismatched_non_empty)} "
        f"missing_shortcards={len(result.missing_shortcards)}"
    )

    if not result.failures:
        print("[hazard_shortcard_guard] PASS")
        return

    print("[hazard_shortcard_guard] FAIL")
    for failure in result.failures:
        print(f" - {failure}")
    if result.backfill_candidates:
        print(
            "   backfill candidates: "
            f"{_preview(result.backfill_candidates, sample_size=args.sample_size)}"
        )
    if result.mismatched_non_empty:
        print(
            "   mismatched non-empty: "
            f"{_preview(result.mismatched_non_empty, sample_size=args.sample_size)}"
        )
    if result.missing_shortcards:
        print(
            "   missing shortcards: "
            f"{_preview(result.missing_shortcards, sample_size=args.sample_size)}"
        )

    raise SystemExit(1)


if __name__ == "__main__":
    main()
