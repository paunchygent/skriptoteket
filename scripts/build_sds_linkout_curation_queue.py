from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_meta(raw_root: Path, cid: str) -> dict:
    meta_path = raw_root / cid / "meta.json"
    if not meta_path.is_file():
        return {}
    return _load_json(meta_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=Path("data/pubchem_payloads/raw"),
    )
    parser.add_argument(
        "--candidates",
        type=Path,
        default=Path("data/sds_linkouts/candidates.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/sds_linkouts/curation_queue.csv"),
    )
    args = parser.parse_args()

    payload = _load_json(args.candidates)
    entries: dict[str, list[dict]] = payload.get("entries", {})

    rows: list[dict[str, str]] = []
    for cid in sorted(entries.keys(), key=lambda value: int(value)):
        meta = _load_meta(args.raw_root, cid)
        for index, candidate in enumerate(entries[cid]):
            rows.append(
                {
                    "cid": cid,
                    "hazard_key": str(meta.get("hazard_key") or ""),
                    "display_name": str(meta.get("display_name") or ""),
                    "compound_url": str(meta.get("compound_url") or ""),
                    "candidate_index": str(index),
                    "candidate_url": str(candidate.get("url") or ""),
                    "candidate_source": str(candidate.get("source") or ""),
                    "likely_sds": str(bool(candidate.get("likely_sds"))).lower(),
                }
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {args.output} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
