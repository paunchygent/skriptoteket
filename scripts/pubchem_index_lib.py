from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

HAZARD_CODE_RE = re.compile(r"\b(EUH\d{3}|H\d{3})\b")
PRECAUTIONARY_CODE_RE = re.compile(r"\bP\d{3}(?:\+P\d{3})*\b")


def sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def find_section(node, heading: str):
    if isinstance(node, dict):
        if node.get("TOCHeading") == heading:
            return node
        for value in node.values():
            found = find_section(value, heading)
            if found:
                return found
    elif isinstance(node, list):
        for item in node:
            found = find_section(item, heading)
            if found:
                return found
    return None


def extract_strings(value) -> list[str]:
    if not isinstance(value, dict):
        return []
    strings = value.get("StringWithMarkup")
    if not isinstance(strings, list):
        return []
    extracted: list[str] = []
    for entry in strings:
        if isinstance(entry, dict):
            text = entry.get("String")
            if isinstance(text, str):
                extracted.append(text.strip())
    return extracted


def extract_pictograms(value) -> list[str]:
    if not isinstance(value, dict):
        return []
    strings = value.get("StringWithMarkup")
    if not isinstance(strings, list):
        return []
    pictograms: list[str] = []
    for entry in strings:
        if not isinstance(entry, dict):
            continue
        for markup in entry.get("Markup") or []:
            if not isinstance(markup, dict):
                continue
            url = markup.get("URL")
            if not isinstance(url, str):
                continue
            match = re.search(r"/(GHS\d{2})\.svg", url)
            if match:
                pictograms.append(match.group(1))
    return sorted(set(pictograms))


def extract_ghs_info(payload: dict) -> dict:
    section = find_section(payload, "GHS Classification")
    if not section:
        return {
            "hazard_codes": [],
            "precautionary_codes": [],
            "signal_word": None,
            "pictograms": [],
        }
    info = section.get("Information") or []
    hazard_strings: list[str] = []
    precautionary_strings: list[str] = []
    signal_words: list[str] = []
    pictograms: list[str] = []
    for item in info:
        if not isinstance(item, dict):
            continue
        name = item.get("Name")
        value = item.get("Value")
        if name == "GHS Hazard Statements":
            hazard_strings.extend(extract_strings(value))
        elif name == "Precautionary Statement Codes":
            precautionary_strings.extend(extract_strings(value))
        elif name == "Signal":
            signal_words.extend(extract_strings(value))
        elif name == "Pictogram(s)":
            pictograms.extend(extract_pictograms(value))

    hazard_codes = sorted(set(HAZARD_CODE_RE.findall(" ".join(hazard_strings))))
    precautionary_codes = sorted(
        set(PRECAUTIONARY_CODE_RE.findall(" ".join(precautionary_strings)))
    )
    signal_word = None
    for candidate in signal_words:
        if candidate.casefold() == "danger":
            signal_word = "Danger"
            break
        if candidate.casefold() == "warning":
            signal_word = "Warning"
    pictograms = sorted(set(pictograms))

    return {
        "hazard_codes": hazard_codes,
        "precautionary_codes": precautionary_codes,
        "signal_word": signal_word,
        "pictograms": pictograms,
    }


def extract_sds_linkout(payload: dict) -> list[dict]:
    linkout = payload.get("Linkout")
    if not isinstance(linkout, dict):
        return []
    entries = linkout.get("ObjUrl")
    if not isinstance(entries, list):
        return []
    sds_entries: list[dict] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get("LinkName") or ""
        subject_types = entry.get("SubjectType") or []
        if isinstance(subject_types, str):
            subject_types = [subject_types]
        if isinstance(subject_types, list):
            subject_types = [str(value) for value in subject_types if value]
        is_sds = (
            "safety" in " ".join(subject_types).casefold()
            or "safety data sheet" in str(name).casefold()
        )
        if not is_sds:
            continue
        sds_entries.append(
            {
                "url": entry.get("Url"),
                "name": entry.get("LinkName"),
                "provider": (entry.get("Provider") or {}).get("Name"),
                "subject_types": subject_types,
            }
        )
    return sds_entries


def build_index_record(
    *,
    cid: int,
    raw_root: Path,
    glossary_path: Path,
    curated_linkouts: dict[str, list[dict]] | None = None,
    candidate_linkouts: dict[str, list[dict]] | None = None,
) -> dict:
    cid_dir = raw_root / str(cid)
    lcss_path = cid_dir / "lcss.json"
    linkout_path = cid_dir / "linkout.json"
    meta_path = cid_dir / "meta.json"
    if not lcss_path.is_file():
        raise FileNotFoundError(lcss_path)
    if not linkout_path.is_file():
        raise FileNotFoundError(linkout_path)
    if not meta_path.is_file():
        raise FileNotFoundError(meta_path)

    lcss_payload = load_json(lcss_path)
    meta = load_json(meta_path)
    glossary = load_json(glossary_path)

    ghs = extract_ghs_info(lcss_payload)
    hazard_sv = {code: glossary["statements"]["hazard"].get(code) for code in ghs["hazard_codes"]}
    precautionary_sv = {
        code: glossary["statements"]["precautionary"].get(code)
        for code in ghs["precautionary_codes"]
    }
    signal_word_sv = None
    if isinstance(ghs["signal_word"], str):
        signal_word_sv = glossary["signal_words"].get(ghs["signal_word"].casefold())

    missing_hazard = [code for code, text in hazard_sv.items() if text is None]
    missing_precautionary = [code for code, text in precautionary_sv.items() if text is None]
    curated = (curated_linkouts or {}).get(str(cid)) or []
    candidates = (candidate_linkouts or {}).get(str(cid)) or []
    sds_linkout = curated

    record = {
        "version": 1,
        "cid": cid,
        "captured_at": meta.get("captured_at"),
        "source": {
            "pubchem_url": meta.get("compound_url"),
            "lcss_sha256": sha256(lcss_path),
            "linkout_sha256": sha256(linkout_path),
            "meta_sha256": sha256(meta_path),
        },
        "clp": {
            "hazard_codes": ghs["hazard_codes"],
            "hazard_statements_sv": hazard_sv,
            "precautionary_codes": ghs["precautionary_codes"],
            "precautionary_statements_sv": precautionary_sv,
            "signal_word": ghs["signal_word"].casefold()
            if isinstance(ghs["signal_word"], str)
            else None,
            "signal_word_sv": signal_word_sv,
            "pictograms": ghs["pictograms"],
        },
        "sds_linkout": sds_linkout,
        "missing": {
            "hazard_statements_sv": missing_hazard,
            "precautionary_statements_sv": missing_precautionary,
            "signal_word_sv": None if signal_word_sv else ghs["signal_word"],
            "sds_linkout": len(sds_linkout) == 0,
        },
        "sds_candidates": candidates,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    return record
