from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.pubchem_index_lib import build_index_record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cid", type=int, required=True)
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
        "--output",
        type=Path,
        default=None,
    )
    args = parser.parse_args()

    record = build_index_record(
        cid=args.cid,
        raw_root=args.raw_root,
        glossary_path=args.glossary,
        curated_linkouts=None,
        candidate_linkouts=None,
    )
    output = args.output or Path("data/pubchem_payloads/index/v1/samples") / f"{args.cid}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
