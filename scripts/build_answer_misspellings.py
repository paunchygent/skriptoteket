"""Build the committed misspelling maps and inflected-word exclusion lexicons.

Run from the repository root:
    pdm run build-answer-misspellings --raw-dir /path/to/private/raw

Only this offline build downloads sources. The request-time producer reads the
committed outputs, using only the Python standard library.
"""

from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter
from pathlib import Path

from scripts.build_answer_misspellings_hunspell import expand_word_forms, parse_rep_rules
from scripts.build_answer_misspellings_sources import (
    KEYBOARD_LAYOUTS,
    SOURCES,
    AttestedPair,
    ensure_raw_sources,
    filter_rep_rules,
    keyboard_neighbours,
    parse_awb_pairs,
    parse_birkbeck_pairs,
    parse_dalaj_pairs,
    parse_for_machines_pairs,
    parse_lovs_pairs,
)
from skriptoteket.domain.curated_apps.exam_workspace.answer_spelling import (
    is_allowed_answer_spelling_variant,
    normalize_answer,
)

OUTPUT = Path("src/skriptoteket/domain/curated_apps/exam_workspace/misspelling_data")


def rank_attested(
    pairs: list[AttestedPair], words: set[str]
) -> tuple[dict[str, list[str]], dict[str, int]]:
    """Rank source tier, then observed pair frequency, then lexical tie-break."""
    frequencies: Counter[tuple[str, str]] = Counter()
    ranks: dict[tuple[str, str], int] = {}
    rejected_real_words = rejected_distance = 0
    for pair in pairs:
        correct, miss = normalize_answer(pair.correct), normalize_answer(pair.miss)
        if miss in words:
            rejected_real_words += 1
            continue
        if not is_allowed_answer_spelling_variant(correct, miss):
            rejected_distance += 1
            continue
        key = (correct, miss)
        frequencies[key] += 1
        ranks[key] = max(ranks.get(key, 0), pair.rank)
    grouped: dict[str, list[str]] = {}
    for correct, miss in sorted(frequencies):
        grouped.setdefault(correct, []).append(miss)
    for correct, variants in grouped.items():
        variants.sort(key=lambda miss: (-ranks[correct, miss], -frequencies[correct, miss], miss))
    stats = {
        "source_rows": len(pairs),
        "real_word_rows_dropped": rejected_real_words,
        "a10_rows_dropped": rejected_distance,
        "attested_pairs": len(frequencies),
        "attested_words": len(grouped),
        "word_forms": len(words),
    }
    for rank, count in sorted(Counter(ranks.values()).items()):
        stats[f"rank_{rank}_pairs"] = count
    return grouped, stats


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def build_payloads(raw: dict[str, Path]) -> tuple[dict[str, bytes], dict[str, object]]:
    """Build bytes without writing, so --check proves deterministic regeneration."""
    pairs = {
        "sv": [
            *parse_dalaj_pairs(raw["dalaj-ged-superlim.zip"]),
            *parse_lovs_pairs(raw["lovs-stavfel.wikitext"].read_text()),
            *parse_awb_pairs(raw["awb-typos.wikitext"].read_text()),
        ],
        "en": [
            *parse_birkbeck_pairs(raw["birkbeck-missp.dat"].read_text(encoding="latin-1")),
            *parse_for_machines_pairs(raw["for-machines.wikitext"].read_text()),
        ],
    }
    payloads: dict[str, bytes] = {}
    summary: dict[str, object] = {}
    for language, dictionary in (("sv", "sv_SE"), ("en", "en_US")):
        forms = expand_word_forms(raw[f"{dictionary}.dic"], raw[f"{dictionary}.aff"])
        words = {normalize_answer(form) for form in forms if form.strip()}
        attested, stats = rank_attested(pairs[language], words)
        rep = filter_rep_rules(parse_rep_rules(raw[f"{dictionary}.aff"]))
        document = {
            "attested": attested,
            "rep": rep,
            "keyboard": keyboard_neighbours(KEYBOARD_LAYOUTS[language]),
        }
        payloads[f"{language}.json"] = _json_bytes(document)
        word_bytes = ("\n".join(sorted(words)) + "\n").encode()
        payloads[f"{language}_words.txt.gz"] = gzip.compress(word_bytes, mtime=0)
        summary[language] = {**stats, "rep_rules": len(rep)}
    manifest = {
        "sources": [
            {"name": source.name, "url": source.url, "sha256": source.sha256} for source in SOURCES
        ],
        "languages": summary,
        "ranking": "source rank descending, pair frequency descending, misspelling lexical",
        "word_forms": "standalone dictionary entries and affix-expanded inflections",
    }
    payloads["BUILD.json"] = _json_bytes(manifest)
    return payloads, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--refresh", action="store_true", help="Redownload pinned raw inputs")
    parser.add_argument("--check", action="store_true", help="Compare, without changing outputs")
    args = parser.parse_args()
    raw = ensure_raw_sources(args.raw_dir, refresh=args.refresh)
    payloads, summary = build_payloads(raw)
    mismatches: list[str] = []
    if not args.check:
        args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in payloads.items():
        target = args.output_dir / name
        if args.check:
            if not target.exists() or target.read_bytes() != payload:
                mismatches.append(name)
        else:
            target.write_bytes(payload)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    if mismatches:
        raise SystemExit(f"Generated misspelling data differs: {', '.join(mismatches)}")
    print("Static data matches" if args.check else "Static data written")


if __name__ == "__main__":
    main()
