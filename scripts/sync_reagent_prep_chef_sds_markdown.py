"""Sync curated Reagensberedning SDS markdown into repo-owned storage.

This script copies SDS markdown files generated under `.artifacts/` into a repo-owned
directory under `data/` so they can be committed and used as the canonical SDS corpus
for the Reagensberedning (Reagent Prep Chef) curated app.

Policy:
- The app is Swedish-first; if a `__sv.md` override exists for a document, it is used and
  written to the destination without the `__sv` suffix (one canonical `.md` per SDS).
- Source files live in ephemeral `.artifacts/` (ignored by git); destination files live in
  `data/` (commit-worthy).
"""

from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SyncItem:
    dest_name: str
    source_path: Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path(".artifacts/sds-corpus/manual-markdown"),
        help="Directory containing generated SDS markdown files.",
    )
    parser.add_argument(
        "--dest-dir",
        type=Path,
        default=Path("data/reagent_prep_chef/sds/markdown"),
        help="Repo-owned destination directory (commit-worthy).",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete destination files not present in the source selection.",
    )
    return parser.parse_args()


def _build_sync_plan(*, source_dir: Path) -> list[SyncItem]:
    if not source_dir.is_dir():
        raise SystemExit(f"Source directory does not exist: {source_dir}")

    base_by_name: dict[str, Path] = {}
    sv_by_base_name: dict[str, Path] = {}

    for path in sorted(source_dir.glob("*.md")):
        name = path.name
        if name.endswith("__sv.md"):
            base_name = name.removesuffix("__sv.md") + ".md"
            sv_by_base_name[base_name] = path
            continue
        base_by_name[name] = path

    selected: list[SyncItem] = []
    names = sorted(set(base_by_name) | set(sv_by_base_name))
    for name in names:
        source_path = sv_by_base_name.get(name) or base_by_name.get(name)
        if source_path is None:
            continue
        selected.append(SyncItem(dest_name=name, source_path=source_path))

    return selected


def _sync_files(*, plan: list[SyncItem], source_dir: Path, dest_dir: Path, clean: bool) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)

    expected = {item.dest_name for item in plan}
    copied = 0
    for item in plan:
        dest_path = dest_dir / item.dest_name
        shutil.copyfile(item.source_path, dest_path)
        copied += 1

    removed = 0
    if clean:
        for path in dest_dir.glob("*.md"):
            if path.name in expected:
                continue
            path.unlink()
            removed += 1

    print(
        f"[sds_md_sync] copied={copied} removed={removed} "
        f"source_dir={source_dir} dest_dir={dest_dir}"
    )


def main() -> None:
    args = _parse_args()
    plan = _build_sync_plan(source_dir=args.source_dir)
    _sync_files(plan=plan, source_dir=args.source_dir, dest_dir=args.dest_dir, clean=args.clean)


if __name__ == "__main__":
    main()
