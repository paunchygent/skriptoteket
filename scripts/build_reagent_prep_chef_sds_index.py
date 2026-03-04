"""Build a repo-owned SDS index from the curated SDS markdown corpus.

This script indexes the committed SDS markdown corpus for Reagensberedning (Reagent Prep Chef)
and produces a deterministic JSON index that the backend can load offline (no HTTP fetch).

Inputs:
- `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/hazards.json`
- `data/reagent_prep_chef/sds/markdown/*.md` (commit-worthy)

Outputs:
- `data/reagent_prep_chef/sds/index.json` (commit-worthy)
- `data/reagent_prep_chef/sds/gaps.md` (commit-worthy; tracks remaining coverage gaps)
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ParsedSdsFilename:
    key: str
    provider: str
    revision: str


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--hazards-path",
        type=Path,
        default=Path(
            "src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/hazards.json"
        ),
    )
    parser.add_argument(
        "--markdown-dir",
        type=Path,
        default=Path("data/reagent_prep_chef/sds/markdown"),
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=Path("data/reagent_prep_chef/sds/files"),
        help=(
            "Optional directory containing SDS PDFs (outside git). Used only to mark `pdf_file_name` "
            "as present when the expected file exists."
        ),
    )
    parser.add_argument(
        "--output-index",
        type=Path,
        default=Path("data/reagent_prep_chef/sds/index.json"),
    )
    parser.add_argument(
        "--output-gaps-md",
        type=Path,
        default=Path("data/reagent_prep_chef/sds/gaps.md"),
    )
    return parser.parse_args()


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_filename(path: Path) -> ParsedSdsFilename:
    stem = path.stem
    parts = stem.split("__")
    key = parts[0]
    provider = parts[1] if len(parts) >= 2 and parts[1] else "unknown"
    revision = parts[2] if len(parts) >= 3 and parts[2] else "undated"
    return ParsedSdsFilename(key=key, provider=provider, revision=revision)


def _revision_sort_key(revision: str) -> tuple[int, int, str]:
    if revision == "undated":
        return (1, 0, "")
    try:
        parsed = date.fromisoformat(revision)
        # Prefer newer dated revisions; "best" should sort first in ascending sorts.
        return (0, -parsed.toordinal(), parsed.isoformat())
    except ValueError:
        return (1, 0, revision)


def _provider_rank(provider: str) -> int:
    # Swedish-first app; prefer suppliers we trust and want to standardize on.
    order = [
        "carlroth",
        "merck",
        "sigmaaldrich",
        "aldrich",
        "thermofisher",
        "fishersci",
        "vwr",
        "avantor",
        "tci",
        "honeywell",
        "external",
    ]
    lowered = provider.strip().lower()
    if lowered in order:
        return order.index(lowered)
    return len(order)


def _select_best_markdown(paths: list[Path]) -> Path:
    def _score(path: Path) -> tuple[int, tuple[int, str], str]:
        parsed = _parse_filename(path)
        return (_provider_rank(parsed.provider), _revision_sort_key(parsed.revision), path.name)

    return sorted(paths, key=_score, reverse=False)[0]


def main() -> None:
    args = _parse_args()
    hazards_payload = _load_json(args.hazards_path)
    if not isinstance(hazards_payload, list):
        raise SystemExit(f"Unexpected hazards payload: {args.hazards_path}")

    markdown_dir = args.markdown_dir
    markdown_files = sorted(markdown_dir.glob("*.md"))

    by_key: dict[str, list[Path]] = {}
    for path in markdown_files:
        parsed = _parse_filename(path)
        by_key.setdefault(parsed.key, []).append(path)

    entries: dict[str, dict[str, object]] = {}
    missing_keys: list[str] = []
    missing_pdfs: list[str] = []

    for item in hazards_payload:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").strip()
        if not key:
            continue

        display_name = str(item.get("display_name") or "").strip() or key

        candidates = by_key.get(key) or []
        if not candidates:
            missing_keys.append(key)
            continue

        selected = _select_best_markdown(candidates)
        parsed_name = _parse_filename(selected)

        pdf_name = selected.with_suffix(".pdf").name
        pdf_path = args.pdf_dir / pdf_name
        pdf_file_name: str | None = pdf_name if pdf_path.is_file() else None
        if pdf_file_name is None:
            missing_pdfs.append(pdf_name)

        entry: dict[str, object] = {
            "key": key,
            "display_name": display_name,
            "sds_ref": key,
            "md_file_name": selected.name,
            "provider": parsed_name.provider,
            "revision": parsed_name.revision,
            "pdf_file_name": pdf_file_name,
        }

        entries[key] = entry

    index_payload = {
        "version": 1,
        "as_of": date.today().isoformat(),
        "entries": entries,
    }
    args.output_index.parent.mkdir(parents=True, exist_ok=True)
    args.output_index.write_text(
        json.dumps(index_payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines: list[str] = []
    lines.append("# SDS gaps (Reagensberedning)\n")
    lines.append(f"- Generated: {date.today().isoformat()}\n")
    lines.append(f"- Hazards total: {len([x for x in hazards_payload if isinstance(x, dict)])}\n")
    lines.append(f"- Indexed: {len(entries)}\n")
    lines.append(f"- Missing markdown: {len(missing_keys)}\n")
    lines.append(f"- Missing PDFs: {len(missing_pdfs)}\n")

    if missing_keys:
        lines.append("\n## Missing SDS markdown\n")
        for key in sorted(missing_keys):
            lines.append(f"- `{key}`\n")

    if missing_pdfs:
        lines.append(
            "\n## Missing PDFs (optional; expected under data/reagent_prep_chef/sds/files)\n"
        )
        for name in sorted(missing_pdfs):
            lines.append(f"- `{name}`\n")

    args.output_gaps_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_gaps_md.write_text("".join(lines), encoding="utf-8")

    print(f"[sds_index_ok] wrote={args.output_index}")
    print(f"[sds_gaps_ok] wrote={args.output_gaps_md}")


if __name__ == "__main__":
    main()
