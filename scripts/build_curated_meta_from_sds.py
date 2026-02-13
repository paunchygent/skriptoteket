from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import requests

from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers import (
    extract_hazard_codes_from_text,
    extract_pdf_text,
    extract_pictograms_from_text,
    extract_signal_word_from_text,
    is_sds_document,
)


@dataclass(frozen=True, slots=True)
class SdsMetaResult:
    url: str
    density_g_ml: Decimal | None
    hazard_codes: list[str]
    pictograms: list[str]
    signal_word: str | None


_DENSITY_UNIT_RE = re.compile(
    r"(?P<value>\d+(?:[.,]\d+)?)\s*(?P<unit>g/cm3|g/cm\^3|g/ml|g/mL|kg/m3|kg/m\^3|g/l|g/L)",
    re.IGNORECASE,
)
_DENSITY_HINT_RE = re.compile(r"\b(density|relative density|specific gravity)\b", re.IGNORECASE)


def _extract_density_from_text(text: str) -> Decimal | None:
    for line in text.splitlines():
        lowered = line.lower()
        if "vapor density" in lowered or "vapour density" in lowered:
            continue
        if not _DENSITY_HINT_RE.search(line):
            continue
        unit_match = _DENSITY_UNIT_RE.search(line)
        if unit_match:
            value = Decimal(unit_match.group("value").replace(",", "."))
            unit = unit_match.group("unit").lower()
            if unit in {"g/cm3", "g/cm^3", "g/ml"}:
                return value
            if unit in {"kg/m3", "kg/m^3"}:
                return (value / Decimal("1000")).quantize(Decimal("0.000001"))
            if unit in {"g/l"}:
                return (value / Decimal("1000")).quantize(Decimal("0.000001"))
            continue
        if "relative density" in lowered or "specific gravity" in lowered:
            match = re.search(r"\d+(?:[.,]\d+)?", line)
            if match:
                return Decimal(match.group(0).replace(",", "."))
    return None


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _fetch_pdf(url: str, timeout: float) -> bytes | None:
    try:
        response = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    except Exception:
        return None
    if response.status_code != 200:
        return None
    if not response.content.startswith(b"%PDF"):
        return None
    return response.content


def _find_sds_meta(urls: list[str], timeout: float) -> SdsMetaResult | None:
    for url in urls:
        body = _fetch_pdf(url, timeout)
        if body is None:
            continue
        text = extract_pdf_text(body)
        if not is_sds_document(text):
            continue
        density = _extract_density_from_text(text)
        hazard_codes = extract_hazard_codes_from_text(text)
        pictograms = extract_pictograms_from_text(text)
        signal_word = extract_signal_word_from_text(text)
        if density is None or not hazard_codes:
            continue
        return SdsMetaResult(
            url=url,
            density_g_ml=density,
            hazard_codes=hazard_codes,
            pictograms=pictograms,
            signal_word=signal_word,
        )
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only-cid", action="append", type=int, default=[])
    parser.add_argument(
        "--curated-linkouts",
        type=Path,
        default=Path("data/sds_linkouts/curated.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/sds_linkouts/curated_meta.json"),
    )
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    args = parser.parse_args()

    curated = _load_json(args.curated_linkouts).get("entries", {})
    targets = [str(cid) for cid in args.only_cid] if args.only_cid else list(curated.keys())
    meta_payload = {"version": 1, "as_of": None, "entries": {}}
    if args.output.is_file():
        meta_payload = _load_json(args.output)
    entries = meta_payload.get("entries") or {}

    for cid in targets:
        urls = [item.get("url") for item in curated.get(str(cid), []) if isinstance(item, dict)]
        urls = [url for url in urls if isinstance(url, str)]
        if not urls:
            print(f"[meta_skip] cid={cid} no urls")
            continue
        meta = _find_sds_meta(urls, args.timeout_seconds)
        if meta is None:
            print(f"[meta_fail] cid={cid} no usable SDS")
            continue
        if meta.density_g_ml is None:
            print(f"[meta_missing_density] cid={cid} url={meta.url}")
            continue
        if not meta.hazard_codes:
            print(f"[meta_missing_hcodes] cid={cid} url={meta.url}")
            continue
        entries[str(cid)] = {
            "density_g_ml": float(meta.density_g_ml),
            "clp_bands": [
                {
                    "min_molarity": None,
                    "max_molarity": None,
                    "hazard_codes": meta.hazard_codes,
                    "pictograms": meta.pictograms,
                    "signal_word": meta.signal_word,
                    "notes": [],
                }
            ],
            "sources": [meta.url],
        }
        print(f"[meta_ok] cid={cid} url={meta.url}")

    meta_payload["entries"] = entries
    meta_payload["as_of"] = meta_payload.get("as_of") or ""
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(meta_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
