from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.pubchem_index_lib import build_index_record
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.hazards_store import (
    InMemoryReagentPrepChefHazardStore,
)


def _hazards_path() -> Path:
    from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef import hazards_store

    return Path(hazards_store.__file__).with_name("hazards.json")


def _select_cids(*, only_cids: list[int], only_hazards: list[str]) -> list[int]:
    if only_cids:
        return list(dict.fromkeys(only_cids))
    store = InMemoryReagentPrepChefHazardStore(hazards_path=_hazards_path())
    hazards = store.list_all()
    if only_hazards:
        wanted = set(only_hazards)
        hazards = [hazard for hazard in hazards if hazard.key in wanted]
    cids = [hazard.pubchem_cid for hazard in hazards if hazard.pubchem_cid is not None]
    return list(dict.fromkeys(cids))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only-cid", action="append", type=int, default=[])
    parser.add_argument("--only-hazard", action="append", default=[])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--strict", action="store_true", help="Fail on any missing data.")
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=Path("data/pubchem_payloads/raw"),
    )
    parser.add_argument(
        "--glossary",
        type=Path,
        default=Path("data/clp_sv/glossary_sv_v1.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/pubchem_payloads/index/v1/records"),
    )
    parser.add_argument(
        "--curated-linkouts",
        type=Path,
        default=Path("data/sds_linkouts/curated.json"),
    )
    parser.add_argument(
        "--candidate-linkouts",
        type=Path,
        default=Path("data/sds_linkouts/candidates.json"),
    )
    parser.add_argument(
        "--progress",
        type=Path,
        default=Path(".artifacts/pubchem-index/progress.jsonl"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(".artifacts/pubchem-index/report.json"),
    )
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    cids = _select_cids(only_cids=args.only_cid, only_hazards=args.only_hazard)
    if args.limit and args.limit > 0:
        cids = cids[: args.limit]
    if not cids:
        raise SystemExit("No CIDs selected.")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.progress.parent.mkdir(parents=True, exist_ok=True)

    totals = {
        "processed": 0,
        "skipped": 0,
        "errors": 0,
        "missing": 0,
    }
    missing_records: list[dict] = []
    error_records: list[dict] = []

    curated_linkouts = {}
    if args.curated_linkouts.is_file():
        curated_linkouts = json.loads(args.curated_linkouts.read_text()).get("entries", {})
    candidate_linkouts = {}
    if args.candidate_linkouts.is_file():
        candidate_linkouts = json.loads(args.candidate_linkouts.read_text()).get("entries", {})

    with args.progress.open("w", encoding="utf-8") as progress_file:
        for cid in cids:
            output_path = args.output_dir / f"{cid}.json"
            if args.skip_existing and output_path.is_file():
                totals["skipped"] += 1
                progress_file.write(
                    json.dumps({"cid": cid, "status": "skipped", "output": str(output_path)}) + "\n"
                )
                progress_file.flush()
                continue
            try:
                record = build_index_record(
                    cid=cid,
                    raw_root=args.raw_root,
                    glossary_path=args.glossary,
                    curated_linkouts=curated_linkouts,
                    candidate_linkouts=candidate_linkouts,
                )
            except Exception as exc:
                totals["errors"] += 1
                error_records.append({"cid": cid, "error": str(exc)})
                progress_file.write(
                    json.dumps({"cid": cid, "status": "error", "error": str(exc)}) + "\n"
                )
                progress_file.flush()
                continue
            output_path.write_text(
                json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            totals["processed"] += 1
            missing = record["missing"]
            has_missing = bool(
                missing["hazard_statements_sv"]
                or missing["precautionary_statements_sv"]
                or missing["signal_word_sv"]
                or missing["sds_linkout"]
            )
            if has_missing:
                totals["missing"] += 1
                missing_records.append(
                    {
                        "cid": cid,
                        "missing": missing,
                    }
                )
            progress_file.write(
                json.dumps(
                    {
                        "cid": cid,
                        "status": "ok",
                        "output": str(output_path),
                        "missing": missing if has_missing else None,
                    }
                )
                + "\n"
            )
            progress_file.flush()

    report = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "total": len(cids),
        "totals": totals,
        "missing": missing_records,
        "errors": error_records,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote report: {args.report}")
    print(
        f"DONE total={len(cids)} processed={totals['processed']} "
        f"missing={totals['missing']} errors={totals['errors']} skipped={totals['skipped']}"
    )

    if args.strict and (totals["missing"] > 0 or totals["errors"] > 0):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
