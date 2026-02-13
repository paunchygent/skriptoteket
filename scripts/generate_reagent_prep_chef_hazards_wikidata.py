from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _hazards_path() -> Path:
    return (
        _repo_root()
        / "src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/hazards.json"
    )


def _load_existing(path: Path) -> list[dict[str, object]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise SystemExit("hazards.json must be a JSON list")
    return [item for item in raw if isinstance(item, dict)]


def _normalize_formula(value: str) -> str:
    normalized = value.strip()
    normalized = normalized.replace("*", "·")
    normalized = normalized.replace(". ", "·")
    return normalized


def _existing_formula_keys(entries: list[dict[str, object]]) -> set[str]:
    keys: set[str] = set()
    for item in entries:
        key = str(item.get("key", "")).strip()
        if key:
            keys.add(_normalize_formula(key))
        aliases = item.get("aliases", [])
        if isinstance(aliases, list):
            for alias in aliases:
                alias_key = str(alias).strip()
                if alias_key:
                    keys.add(_normalize_formula(alias_key))
    return keys


_SUBSCRIPT_DIGITS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def _to_wikidata_formula(formula: str) -> str:
    segments: list[str] = []
    for segment in _normalize_formula(formula).split("·"):
        segment = segment.strip()
        if not segment:
            continue

        leading_digits = ""
        rest = segment
        while rest and rest[0].isdigit():
            leading_digits += rest[0]
            rest = rest[1:]

        segments.append(leading_digits + rest.translate(_SUBSCRIPT_DIGITS))
    return "·".join(segments)


def _wikidata_query_pairs(pairs: list[tuple[str, str]]) -> str:
    values = " ".join(f"({json.dumps(formula)} {json.dumps(key)})" for formula, key in pairs)
    # wdt:P274 = chemical formula
    return f"""
SELECT ?key ?item ?itemLabel WHERE {{
  VALUES (?formula ?key) {{ {values} }}
  ?item wdt:P274 ?formula .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "sv". }}
}}
""".strip()


def _fetch_wikidata_labels(*, formulas: list[str], sleep_s: float) -> dict[str, list[str]]:
    """Return {original_formula: [sv_labels...]} using Wikidata chemical formula (P274).

    Wikidata commonly stores element counts as unicode subscripts (e.g. AlCl₃). We convert
    plain formulas to that representation for matching.
    """

    by_formula: dict[str, list[str]] = defaultdict(list)
    if not formulas:
        return {}

    pairs = [(_to_wikidata_formula(formula), formula) for formula in formulas]
    query = _wikidata_query_pairs(pairs)
    url = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(query)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Skriptoteket/1.0 (hazards dataset; https://skriptoteket.hule.education)"
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    bindings = payload.get("results", {}).get("bindings", [])
    if not isinstance(bindings, list):
        return {}

    for row in bindings:
        if not isinstance(row, dict):
            continue
        formula = row.get("key", {}).get("value")
        label = row.get("itemLabel", {}).get("value")
        if not isinstance(formula, str) or not isinstance(label, str):
            continue
        by_formula[formula].append(label)

    if sleep_s > 0:
        time.sleep(sleep_s)
    return dict(by_formula)


def _capitalize_sv(name: str) -> str:
    trimmed = name.strip()
    if not trimmed:
        return trimmed
    return trimmed[:1].upper() + trimmed[1:]


def _aliases_for_formula(formula: str) -> list[str]:
    aliases: list[str] = []
    if "·" in formula:
        aliases.append(formula.replace("·", "."))
        aliases.append(formula.replace("·", "*"))
    return aliases


def _build_entry(*, formula: str, display_name: str) -> dict[str, object]:
    return {
        "key": formula,
        "display_name": display_name,
        "hazard_codes": [],
        "ppe": ["Skyddsglasögon"],
        "disposal": "Följ lokala rutiner och SDS.",
        "notes": [],
        "aliases": _aliases_for_formula(formula),
        "search_aliases": [],
        "pubchem_cid": None,
    }


def _chunks(values: list[str], size: int) -> list[list[str]]:
    return [values[i : i + size] for i in range(0, len(values), size)]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate reagent_prep_chef hazards entries from Wikidata labels."
    )
    parser.add_argument("--write", action="store_true", help="Write merged hazards.json in-place.")
    parser.add_argument("--batch-size", type=int, default=40)
    parser.add_argument("--sleep-s", type=float, default=0.2)
    args = parser.parse_args()

    hazards_path = _hazards_path()
    existing = _load_existing(hazards_path)
    existing_keys = _existing_formula_keys(existing)

    # Candidate formulas (aim: +100 new, common in school chemistry labs).
    candidates = [
        "Na3PO4",
        "Na2HPO4·12H2O",
        "NaH2PO4·H2O",
        "K3PO4",
        "CaHPO4",
        "(NH4)2HPO4",
        "(NH4)3PO4",
        "Mg3(PO4)2",
        "Zn3(PO4)2",
        "AlPO4",
        "Na4P2O7",
        "Na5P3O10",
        "Li2CO3",
        "MgCO3",
        "SrCO3",
        "BaCO3",
        "ZnCO3",
        "CuCO3",
        "FeCO3",
        "MnCO3",
        "CoCO3",
        "NiCO3",
        "Na2CO3·H2O",
        "Mg(OH)2",
        "Al(OH)3",
        "Fe(OH)2",
        "Fe(OH)3",
        "Cu(OH)2",
        "Zn(OH)2",
        "Ba(OH)2",
        "Ba(OH)2·8H2O",
        "Sr(OH)2",
        "Sr(OH)2·8H2O",
        "LiOH",
        "CaO",
        "MgO",
        "Al2O3",
        "Fe2O3",
        "Fe3O4",
        "CuO",
        "Cu2O",
        "ZnO",
        "MnO2",
        "SiO2",
        "Na2O",
        "K2O",
        "PbO",
        "PbO2",
        "SnO2",
        "HBr",
        "HI",
        "HF",
        "LiNO3",
        "Mg(NO3)2",
        "Mg(NO3)2·6H2O",
        "Zn(NO3)2",
        "Zn(NO3)2·6H2O",
        "Co(NO3)2",
        "Co(NO3)2·6H2O",
        "Ni(NO3)2",
        "Ni(NO3)2·6H2O",
        "Al(NO3)3",
        "Al(NO3)3·9H2O",
        "Ca(NO3)2·4H2O",
        "Li2SO4",
        "Al2(SO4)3",
        "Fe2(SO4)3",
        "NiSO4",
        "NiSO4·6H2O",
        "CoSO4",
        "CoSO4·7H2O",
        "MnSO4",
        "MnSO4·H2O",
        "MnSO4·4H2O",
        "ZnSO4",
        "CuSO4·H2O",
        "SrSO4",
        "BaCl2",
        "MgCl2",
        "AlCl3",
        "FeCl3",
        "FeCl2",
        "CuCl2",
        "NiCl2",
        "CoCl2",
        "MnCl2",
        "MnCl2·4H2O",
        "SnCl2",
        "SnCl2·2H2O",
        "CaBr2",
        "CaI2",
        "KBrO3",
        "NaBrO3",
        "KIO3",
        "NaIO3",
        "KIO4",
        "NaIO4",
        "KClO4",
        "NaClO4",
        "Na2SiO3",
        "K2SiO3",
        "Na2S",
        "Na2S·9H2O",
        "FeS",
        "ZnS",
        "CuS",
        "NH4SCN",
        "Na2S2O3",
        "NaHSO4",
        "KHSO4",
        "Na2Cr2O7",
        "Na2Cr2O7·2H2O",
        "(NH4)2Cr2O7",
        "CaC2",
        "K2C2O4",
        "KHC2O4",
        "NaHC2O4",
        "H2C2O4",
        "CaC2O4",
        "MgC2O4",
        "KAl(SO4)2·12H2O",
        "NH4Al(SO4)2·12H2O",
        "CH4N2O",
        "C7H6O2",
        "C7H6O3",
        "C4H6O6",
        "C3H6O3",
        "C6H8O6",
        "C3H8O3",
        "C14H14N3NaO3S",
        "C15H15N3O2",
        "C27H28Br2O5S",
        "C28H30O4",
        "Sn",
        "Pb",
        "Ni",
        "Co",
        "Mn",
        "Ag",
        "S",
    ]

    normalized_candidates = [_normalize_formula(value) for value in candidates]
    targets = sorted({value for value in normalized_candidates if value not in existing_keys})

    if not targets:
        print("No new formulas to add.", file=sys.stderr)
        return

    resolved: dict[str, str] = {}
    missing: list[str] = []
    ambiguous: dict[str, list[str]] = {}

    manual_labels: dict[str, str] = {
        "Al2(SO4)3": "Aluminiumsulfat",
        "Al(NO3)3·9H2O": "Aluminiumnitrat (nonahydrat)",
        "Ba(OH)2·8H2O": "Bariumhydroxid (oktahydrat)",
        "BaCO3": "Bariumkarbonat",
        "CaBr2": "Kalciumbromid",
        "CaI2": "Kalciumjodid",
        "CaC2O4": "Kalciumoxalat",
        "C14H14N3NaO3S": "Metylorange",
        "C15H15N3O2": "Metylrött",
        "C27H28Br2O5S": "Bromtymolblått",
        "C28H30O4": "Tymolftalein",
        "C6H8O6": "Askorbinsyra",
        "C7H6O2": "Bensoesyra",
        "C7H6O3": "Salicylsyra",
        "C4H6O6": "Vinsyra",
        "CH4N2O": "Urea (karbamid)",
        "K3PO4": "Kaliumfosfat",
        "K2C2O4": "Kaliumoxalat",
        "KHSO4": "Kaliumvätesulfat",
        "KIO3": "Kaliumjodat",
        "KBrO3": "Kaliumbromat",
        "LiBr": "Litiumbromid",
        "LiF": "Litiumfluorid",
        "LiI": "Litiumjodid",
        "LiNO3": "Litiumnitrat",
        "Li2SO4": "Litiumsulfat",
        "MgBr2": "Magnesiumbromid",
        "MgC2O4": "Magnesiumoxalat",
        "MgF2": "Magnesiumfluorid",
        "MgI2": "Magnesiumjodid",
        "NH4Br": "Ammoniumbromid",
        "NH4F": "Ammoniumfluorid",
        "NH4I": "Ammoniumjodid",
        "Na2B4O7": "Natriumtetraborat",
        "Na2B4O7·5H2O": "Natriumtetraborat (pentahydrat)",
        "Na2CO3·H2O": "Natriumkarbonat (monohydrat)",
        "Na2Cr2O7": "Natriumdikromat",
        "Na2Cr2O7·2H2O": "Natriumdikromat (dihydrat)",
        "Na2HPO4·12H2O": "Dinatriumhydrogenfosfat (dodekahydrat)",
        "Na4P2O7": "Natriumpyrofosfat",
        "Na5P3O10": "Natriumtripolyfosfat",
        "NaBrO3": "Natriumbromat",
        "NaHC2O4": "Natriumväteoxalat",
        "NaH2PO4·H2O": "Natriumdihydrogenfosfat (monohydrat)",
        "NaIO3": "Natriumjodat",
        "(NH4)2Cr2O7": "Ammoniumdikromat",
        "KAl(SO4)2·12H2O": "Kaliumalun (dodekahydrat)",
        "NH4Al(SO4)2·12H2O": "Ammoniumalun (dodekahydrat)",
        "Na3PO4": "Natriumfosfat (anhydrat)",
    }

    def is_wikidata_qid(value: str) -> bool:
        return value.startswith("Q") and value[1:].isdigit()

    suffix_preference = [
        "oxid",
        "hydroxid",
        "klorid",
        "bromid",
        "jodid",
        "fluorid",
        "nitrat",
        "sulfat",
        "karbonat",
        "fosfat",
        "silikat",
        "sulfid",
        "kromat",
        "dikromat",
        "tiosulfat",
        "persulfat",
        "peroxid",
        "oxalat",
        "acetat",
        "syra",
        "alun",
    ]

    for batch in _chunks(targets, args.batch_size):
        labels_by_formula = _fetch_wikidata_labels(formulas=batch, sleep_s=args.sleep_s)
        for formula in batch:
            labels = labels_by_formula.get(formula, [])
            unique_labels = sorted(
                {
                    label.strip()
                    for label in labels
                    if label.strip() and not is_wikidata_qid(label.strip())
                }
            )
            if len(unique_labels) == 1:
                resolved[formula] = _capitalize_sv(unique_labels[0])
            elif len(unique_labels) == 0:
                manual = manual_labels.get(formula)
                if manual:
                    resolved[formula] = manual
                else:
                    missing.append(formula)
            else:
                lowered = [(label, label.casefold()) for label in unique_labels]
                preferred = [
                    label
                    for label, folded in lowered
                    if any(suffix in folded for suffix in suffix_preference)
                ]
                if len(preferred) == 1:
                    resolved[formula] = _capitalize_sv(preferred[0])
                else:
                    manual = manual_labels.get(formula)
                    if manual:
                        resolved[formula] = manual
                    else:
                        ambiguous[formula] = unique_labels

    new_entries = [
        _build_entry(formula=formula, display_name=name)
        for formula, name in sorted(resolved.items())
    ]

    print(f"Existing entries: {len(existing)}", file=sys.stderr)
    print(f"Candidates (after de-dupe): {len(targets)}", file=sys.stderr)
    print(f"Resolved (sv label, unique): {len(new_entries)}", file=sys.stderr)
    print(f"Missing labels: {len(missing)}", file=sys.stderr)
    print(f"Ambiguous formulas: {len(ambiguous)}", file=sys.stderr)

    if missing:
        print(
            "Missing:",
            ", ".join(missing[:25]) + (" ..." if len(missing) > 25 else ""),
            file=sys.stderr,
        )
    if ambiguous:
        sample = list(ambiguous.items())[:10]
        print("Ambiguous sample:", file=sys.stderr)
        for formula, labels in sample:
            print(f"  {formula}: {labels[:3]}", file=sys.stderr)

    merged = existing + new_entries
    merged_sorted = sorted(
        merged,
        key=lambda item: (
            str(item.get("display_name", "")).casefold(),
            str(item.get("key", "")).casefold(),
        ),
    )

    output = json.dumps(merged_sorted, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        hazards_path.write_text(output, encoding="utf-8")
        print(f"Wrote hazards: {hazards_path}", file=sys.stderr)
        return

    print(output)


if __name__ == "__main__":
    main()
