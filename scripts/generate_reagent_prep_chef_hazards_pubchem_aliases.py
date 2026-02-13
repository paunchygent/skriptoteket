from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from scripts.pubchem_aliases_lib import load_hazards, run_alias_generation


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _hazards_path() -> Path:
    return (
        _repo_root()
        / "src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/hazards.json"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate validated English aliases for hazards via PubChem."
    )
    parser.add_argument(
        "--write", action="store_true", help="Write search_aliases to hazards.json."
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Allow writing even if some entries are missing/ambiguous.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(".artifacts/pubchem-aliases/report.json"),
        help="Where to write the JSON report.",
    )
    parser.add_argument(
        "--progress",
        type=Path,
        default=Path(".artifacts/pubchem-aliases/progress.jsonl"),
        help="Write progress JSONL entries here (set to empty to disable).",
    )
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=10,
        help="Write a partial report every N records (0 to disable).",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Number of hazards to process concurrently.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Max CIDs per PubChem properties request.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit the number of hazards processed (0 = no limit).",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Process only these hazard keys (can be repeated).",
    )
    parser.add_argument(
        "--skip",
        action="append",
        default=[],
        help="Skip these hazard keys (can be repeated).",
    )
    parser.add_argument(
        "--require-cid",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="Require pubchem_cid for every hazard (no fallback resolution).",
    )
    args = parser.parse_args()

    hazards = load_hazards(_hazards_path())
    if args.only:
        only_set = {value.strip() for value in args.only if value.strip()}
        hazards = [record for record in hazards if record.key in only_set]
    if args.skip:
        skip_set = {value.strip() for value in args.skip if value.strip()}
        hazards = [record for record in hazards if record.key not in skip_set]
    if args.limit and args.limit > 0:
        hazards = hazards[: args.limit]

    progress_path = args.progress if str(args.progress).strip() else None

    asyncio.run(
        run_alias_generation(
            hazards=hazards,
            hazards_path=_hazards_path(),
            output_path=args.report,
            write=args.write,
            allow_partial=args.allow_partial,
            concurrency=args.concurrency,
            batch_size=args.batch_size,
            progress_path=progress_path,
            checkpoint_every=args.checkpoint_every,
            require_cid=args.require_cid,
        )
    )


if __name__ == "__main__":
    main()
