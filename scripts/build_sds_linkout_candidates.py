from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers.pubchem_extractors import (
    extract_candidate_urls,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_pdf_providers import (
    is_possible_pdf_url,
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_likely_sds(url: str) -> bool:
    lowered = url.lower()
    return any(token in lowered for token in ("sds", "msds", "safety-data-sheet"))


def _collect_urls(*, payload_path: Path, source: str) -> list[dict]:
    payload = _load_json(payload_path)
    urls = extract_candidate_urls(payload)
    candidates: list[dict] = []
    for url in urls:
        if not is_possible_pdf_url(url):
            continue
        candidates.append(
            {
                "url": url,
                "source": source,
                "likely_sds": _is_likely_sds(url),
            }
        )
    return candidates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=Path("data/pubchem_payloads/raw"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/sds_linkouts/candidates.json"),
    )
    args = parser.parse_args()

    entries: dict[str, list[dict]] = {}
    for cid_dir in sorted(args.raw_root.iterdir(), key=lambda p: p.name):
        cid = cid_dir.name
        candidates: list[dict] = []
        safety_path = cid_dir / "safety.json"
        if safety_path.is_file():
            candidates.extend(_collect_urls(payload_path=safety_path, source="safety"))
        lcss_path = cid_dir / "lcss.json"
        if lcss_path.is_file():
            candidates.extend(_collect_urls(payload_path=lcss_path, source="lcss"))
        linkout_path = cid_dir / "linkout.json"
        if linkout_path.is_file():
            candidates.extend(_collect_urls(payload_path=linkout_path, source="linkout"))
        if candidates:
            # de-dupe by url
            seen: set[str] = set()
            deduped: list[dict] = []
            for candidate in candidates:
                url = candidate["url"]
                if url in seen:
                    continue
                seen.add(url)
                deduped.append(candidate)
            entries[cid] = deduped

    payload = {
        "version": 1,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "entries": entries,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.output} ({len(entries)} CIDs with candidates)")


if __name__ == "__main__":
    main()
