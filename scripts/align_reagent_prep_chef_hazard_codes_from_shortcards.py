"""Align Reagent Prep Chef hazard H-codes with SDS shortcards (offline).

Purpose:
    Compare committed `hazards.json` against committed `shortcards.json` and
    optionally backfill missing hazard H-codes in hazards entries.

Relationships:
    - Reads `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/hazards.json`.
    - Reads `data/reagent_prep_chef/sds/shortcards.json`.
    - Writes alignment report under `.artifacts/`.
    - Optionally writes updated hazards back to `hazards.json` (`--apply`).
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_HAZARDS_PATH = Path(
    "src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/hazards.json"
)
DEFAULT_SHORTCARDS_PATH = Path("data/reagent_prep_chef/sds/shortcards.json")
DEFAULT_REPORT_PATH = Path(".artifacts/reagent_prep_chef/hazard-sds-alignment-report.json")

H_CODE_PATTERN = re.compile(r"^H[0-9]{3}$")


@dataclass(frozen=True, slots=True)
class AlignmentResult:
    """Result of comparing hazards and shortcards hazard codes."""

    backfill_by_key: dict[str, list[str]]
    mismatched_non_empty: list[str]
    missing_shortcards: list[str]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hazards-path", type=Path, default=DEFAULT_HAZARDS_PATH)
    parser.add_argument("--shortcards-path", type=Path, default=DEFAULT_SHORTCARDS_PATH)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write backfilled hazard_codes into hazards.json.",
    )
    parser.add_argument(
        "--allow-manual-validation-pending",
        action="store_true",
        help=(
            "Allow --apply even when shortcards declare manual validation required. "
            "Use only after explicit human review."
        ),
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


def _normalize_h_codes(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    values: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            continue
        normalized = item.strip().upper()
        if not H_CODE_PATTERN.match(normalized):
            continue
        values.add(normalized)
    return sorted(values)


def _shortcards_by_ref(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    entries = payload.get("entries")
    if not isinstance(entries, list):
        return {}

    result: dict[str, dict[str, object]] = {}
    for item in entries:
        if not isinstance(item, dict):
            continue
        key = item.get("sds_ref")
        if not isinstance(key, str):
            continue
        result[key] = item
    return result


def _manual_validation_required(payload: dict[str, object]) -> bool:
    manual_validation = payload.get("manual_validation")
    if not isinstance(manual_validation, dict):
        return False
    required = manual_validation.get("required")
    return bool(required) if isinstance(required, bool) else False


def collect_alignment(
    *,
    hazards: list[dict[str, object]],
    shortcards_payload: dict[str, object],
) -> AlignmentResult:
    """Collect hazard-code alignment actions without mutating input payloads.

    Args:
        hazards: Parsed hazards entries from `hazards.json`.
        shortcards_payload: Parsed shortcards payload from `shortcards.json`.

    Returns:
        AlignmentResult with:
          - `backfill_by_key`: keys that can be safely backfilled (empty -> shortcard h-codes),
          - `mismatched_non_empty`: keys where both sides have non-empty but different codes,
          - `missing_shortcards`: hazard keys without matching shortcard entry.
    """
    shortcards = _shortcards_by_ref(shortcards_payload)
    backfill_by_key: dict[str, list[str]] = {}
    mismatched_non_empty: list[str] = []
    missing_shortcards: list[str] = []

    for hazard in hazards:
        key = hazard.get("key")
        if not isinstance(key, str):
            continue

        shortcard = shortcards.get(key)
        if shortcard is None:
            missing_shortcards.append(key)
            continue

        hazard_codes = _normalize_h_codes(hazard.get("hazard_codes"))
        shortcard_clp = shortcard.get("clp")
        shortcard_codes = _normalize_h_codes(
            shortcard_clp.get("h_codes") if isinstance(shortcard_clp, dict) else []
        )

        if not hazard_codes and shortcard_codes:
            backfill_by_key[key] = shortcard_codes
            continue
        if hazard_codes and shortcard_codes and hazard_codes != shortcard_codes:
            mismatched_non_empty.append(key)

    return AlignmentResult(
        backfill_by_key=dict(sorted(backfill_by_key.items())),
        mismatched_non_empty=sorted(mismatched_non_empty),
        missing_shortcards=sorted(missing_shortcards),
    )


def apply_backfill(
    *,
    hazards: list[dict[str, object]],
    backfill_by_key: dict[str, list[str]],
) -> list[dict[str, object]]:
    """Apply hazard-code backfills to a hazards payload copy."""
    updated: list[dict[str, object]] = []
    for hazard in hazards:
        item = dict(hazard)
        key = item.get("key")
        if isinstance(key, str) and key in backfill_by_key:
            item["hazard_codes"] = list(backfill_by_key[key])
        updated.append(item)
    return updated


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    args = _parse_args()
    hazards = _load_hazards(args.hazards_path)
    shortcards_payload = _load_shortcards(args.shortcards_path)
    alignment = collect_alignment(hazards=hazards, shortcards_payload=shortcards_payload)

    manual_validation_required = _manual_validation_required(shortcards_payload)
    if args.apply and manual_validation_required and not args.allow_manual_validation_pending:
        raise SystemExit(
            "Refusing --apply because shortcards require manual validation. "
            "Resolve manual validation or pass --allow-manual-validation-pending."
        )

    updated_hazards = apply_backfill(hazards=hazards, backfill_by_key=alignment.backfill_by_key)
    if args.apply:
        _write_json(args.hazards_path, updated_hazards)

    report_payload = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "paths": {
            "hazards_path": str(args.hazards_path),
            "shortcards_path": str(args.shortcards_path),
            "applied": args.apply,
        },
        "summary": {
            "hazards_entries": len(hazards),
            "shortcards_entries": len(_shortcards_by_ref(shortcards_payload)),
            "backfill_candidates": len(alignment.backfill_by_key),
            "mismatched_non_empty": len(alignment.mismatched_non_empty),
            "missing_shortcards": len(alignment.missing_shortcards),
            "manual_validation_required": manual_validation_required,
        },
        "backfill_candidates": [
            {"key": key, "h_codes": codes} for key, codes in alignment.backfill_by_key.items()
        ],
        "mismatched_non_empty": alignment.mismatched_non_empty,
        "missing_shortcards": alignment.missing_shortcards,
    }
    _write_json(args.report_path, report_payload)

    print(f"[hazard_sds_alignment_report] wrote={args.report_path}")
    print(
        "[hazard_sds_alignment_summary] "
        f"backfill_candidates={len(alignment.backfill_by_key)} "
        f"mismatched_non_empty={len(alignment.mismatched_non_empty)} "
        f"missing_shortcards={len(alignment.missing_shortcards)} "
        f"applied={args.apply}"
    )
    if args.apply:
        print(f"[hazard_sds_alignment_apply] wrote={args.hazards_path}")


if __name__ == "__main__":
    main()
