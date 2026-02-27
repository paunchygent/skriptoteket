"""PubChem PUG-View extraction helpers for Reagent Prep Chef SDS derivation.

This module extracts small, typed signals from PubChem JSON payloads used by the
Reagent Prep Chef SDS pipeline (GHS snapshot + density + URL discovery).

Related:
  - `sds_fetcher.py` (orchestrates PubChem + PDF derivation)
  - `sds_parsers/text_extractors.py` (PDF text heuristics)
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Iterable, Literal

from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers.patterns import (
    HAZARD_CODE_RE,
    NON_HAZARDOUS_RE,
    PICTOGRAM_RE,
)

_DENSITY_UNIT_RE = re.compile(
    r"(?P<value>\d+(?:[.,]\d+)?)\s*(?P<unit>"
    r"g\s*/\s*(?:cm3|cm\^3|cm³|cu\s*cm|cc|ml|mL|l|L)"
    r"|kg\s*/\s*(?:m3|m\^3|m³)"
    r")",
    re.IGNORECASE,
)
_SPECIFIC_GRAVITY_RE = re.compile(r"\b(specific gravity|relative density)\b", re.IGNORECASE)
_DECIMAL_VALUE_RE = re.compile(r"\d+(?:[.,]\d+)?")


def extract_pubchem_ghs(
    pug_view: dict,
) -> tuple[list[str], list[str], Literal["danger", "warning"] | None]:
    """Extract GHS hazard codes, pictograms, and signal word from PubChem PUG-View."""
    ghs_section = _find_section_by_heading(pug_view, "GHS Classification")
    if ghs_section is None:
        return ([], [], None)

    hazard_codes: list[str] = []
    pictograms: list[str] = []
    signal_word: Literal["danger", "warning"] | None = None

    for info in _iter_information(ghs_section):
        name = info.get("Name")
        value = info.get("Value", {})
        if name == "GHS Hazard Statements":
            for text in _iter_string_values(value):
                hazard_codes.extend(HAZARD_CODE_RE.findall(text))
        elif name == "Pictogram(s)":
            for entry in _iter_markup_values(value):
                url = entry.get("URL")
                if not isinstance(url, str):
                    continue
                code = _extract_pictogram_code(url)
                if code:
                    pictograms.append(code)
        elif name == "Signal":
            for text in _iter_string_values(value):
                normalized = text.strip().lower()
                if normalized == "danger":
                    signal_word = "danger"
                elif normalized == "warning":
                    signal_word = "warning"

    hazard_codes = sorted(set(hazard_codes))
    pictograms = sorted(set(pictograms))
    return (hazard_codes, pictograms, signal_word)


def extract_pubchem_nonhazardous(pug_view: dict) -> bool:
    """Return True if PubChem GHS section includes a non-hazardous statement."""
    ghs_section = _find_section_by_heading(pug_view, "GHS Classification")
    if ghs_section is None:
        return False
    for info in _iter_information(ghs_section):
        value = info.get("Value", {})
        for text in _iter_string_values(value):
            if NON_HAZARDOUS_RE.search(text):
                return True
    return False


def extract_pug_view_section_text(payload: dict, *, headings: Iterable[str]) -> str:
    """Extract text content from named PUG-View headings."""
    chunks: list[str] = []
    for heading in headings:
        section = _find_section_by_heading(payload, heading)
        if section is None:
            continue
        for info in _iter_information(section):
            value = info.get("Value", {})
            for text in _iter_string_values(value):
                chunks.append(text)
    return "\n".join(chunks)


def extract_candidate_urls(payload: object) -> list[str]:
    """Collect all URL-like strings found in a PUG-View payload."""
    urls: set[str] = set()

    def walk(value: object) -> None:
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, str):
            if value.startswith("http://") or value.startswith("https://"):
                urls.add(value)

    walk(payload)
    return sorted(urls)


def extract_density_g_ml(pug_view: dict) -> Decimal | None:
    """Extract density in g/mL from PubChem PUG-View density heading."""
    text = extract_pug_view_section_text(pug_view, headings=("Density",))
    if not text:
        return None
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        unit_match = _DENSITY_UNIT_RE.search(line)
        if unit_match:
            value = _decimal_from_text(unit_match.group("value"))
            if value is None:
                continue
            unit = re.sub(r"\s+", "", unit_match.group("unit")).lower()
            unit = unit.replace("³", "3")
            if unit in {"g/cm3", "g/cm^3", "g/cucm", "g/cc", "g/ml"}:
                return value
            if unit in {"kg/m3", "kg/m^3"}:
                return (value / Decimal("1000")).quantize(Decimal("0.000001"))
            if unit in {"g/l"}:
                return (value / Decimal("1000")).quantize(Decimal("0.000001"))
        if _SPECIFIC_GRAVITY_RE.search(line):
            number = _DECIMAL_VALUE_RE.search(line)
            if number:
                value = _decimal_from_text(number.group(0))
                if value is not None:
                    return value
    return None


def _find_section_by_heading(payload: dict, heading: str) -> dict | None:
    def walk(section: dict) -> dict | None:
        if section.get("TOCHeading") == heading:
            return section
        for child in section.get("Section", []) or []:
            if isinstance(child, dict):
                found = walk(child)
                if found is not None:
                    return found
        return None

    record = payload.get("Record")
    if not isinstance(record, dict):
        return None
    for section in record.get("Section", []) or []:
        if isinstance(section, dict):
            found = walk(section)
            if found is not None:
                return found
    return None


def _iter_information(section: dict) -> Iterable[dict]:
    for info in section.get("Information", []) or []:
        if isinstance(info, dict):
            yield info
    for child in section.get("Section", []) or []:
        if isinstance(child, dict):
            yield from _iter_information(child)


def _iter_string_values(value: dict) -> Iterable[str]:
    strings = value.get("StringWithMarkup")
    if not isinstance(strings, list):
        return
    for item in strings:
        if isinstance(item, dict):
            text = item.get("String")
            if isinstance(text, str):
                yield text


def _iter_markup_values(value: dict) -> Iterable[dict]:
    strings = value.get("StringWithMarkup")
    if not isinstance(strings, list):
        return
    for item in strings:
        if isinstance(item, dict):
            for markup in item.get("Markup", []) or []:
                if isinstance(markup, dict):
                    yield markup


def _extract_pictogram_code(url: str) -> str | None:
    match = PICTOGRAM_RE.search(url)
    if not match:
        return None
    return match.group(0).upper()


def _decimal_from_text(value: str) -> Decimal | None:
    cleaned = value.strip().replace(",", ".")
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except Exception:
        return None
