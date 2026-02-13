from __future__ import annotations

import re
from typing import Iterable

from skriptoteket.domain.curated_apps.reagent_prep_chef.models import ExothermicityLevel
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers.pdf_text import (
    extract_pdf_text,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers.sections import (
    extract_section,
)

_BOILERPLATE_PATTERNS = [
    re.compile(r"^section\s*\d+", re.IGNORECASE),
    re.compile(r"stability\s+and\s+reactivity", re.IGNORECASE),
    re.compile(r"materials with which the chemical could react", re.IGNORECASE),
    re.compile(r"could react to produce a hazardous situation", re.IGNORECASE),
    re.compile(r"will react or polymerize", re.IGNORECASE),
    re.compile(r"release excess pressure or heat", re.IGNORECASE),
    re.compile(r"create other hazardous", re.IGNORECASE),
    re.compile(r"list of all conditions that should be avoided", re.IGNORECASE),
    re.compile(r"static discharge.*shock.*vibrations", re.IGNORECASE),
    re.compile(r"because of use, storage, or heating", re.IGNORECASE),
    re.compile(r"hazardous combustion products should also be included", re.IGNORECASE),
]


def parse_sds_heuristics_from_pdf(
    pdf_bytes: bytes,
) -> tuple[list[str], ExothermicityLevel | None, list[str]]:
    """Extract heuristics (incompatibilities, exothermicity, reaction notes) from PDF."""
    text = extract_pdf_text(pdf_bytes)
    return parse_sds_heuristics_from_text(text)


def parse_sds_heuristics_from_text(
    text: str,
) -> tuple[list[str], ExothermicityLevel | None, list[str]]:
    """Extract heuristics from SDS text (Section 10 preferred)."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    section_text = extract_section(lines, section_number="10")
    if not section_text:
        return ([], None, [])
    return parse_sds_heuristics_from_section_text(section_text)


def parse_sds_heuristics_from_section_text(
    section_text: str,
) -> tuple[list[str], ExothermicityLevel | None, list[str]]:
    """Extract heuristics from a section-scoped text payload."""
    section_lines = [line.strip() for line in section_text.splitlines() if line.strip()]

    incompatibilities = _extract_field_values(
        section_text,
        labels=("Incompatible materials", "Incompatibilities", "Inkompatibla material"),
    )
    reaction_notes = _extract_field_values(
        section_text,
        labels=(
            "Hazardous reactions",
            "Hazardous decomposition products",
            "Conditions to avoid",
            "Farliga reaktioner",
            "Farliga sönderdelningsprodukter",
        ),
    )

    if not incompatibilities:
        incompatibilities = _scan_for_keywords(
            section_lines,
            keywords=("incompatible", "incompatib", "inkompatib"),
        )

    if not reaction_notes:
        reaction_notes = _scan_for_keywords(
            section_lines,
            keywords=(
                "hazardous reaction",
                "dangerous reaction",
                "stability",
                "stable",
                "conditions to avoid",
                "farliga reaktioner",
                "stabil",
            ),
        )
    exothermicity = _infer_exothermicity(section_text)

    if incompatibilities and reaction_notes:
        incompat_lower = {value.lower() for value in incompatibilities}
        reaction_notes = [value for value in reaction_notes if value.lower() not in incompat_lower]

    return (incompatibilities, exothermicity, reaction_notes)


def _extract_field_values(section_text: str, labels: Iterable[str]) -> list[str]:
    values: list[str] = []
    lines = [line.strip() for line in section_text.splitlines() if line.strip()]
    for label in labels:
        pattern = re.compile(rf"{re.escape(label)}\s*[:\-]\s*(.+)", re.IGNORECASE)
        for index, line in enumerate(lines):
            match = pattern.search(line)
            if match:
                value = match.group(1).strip()
                if value:
                    values.append(value)
                continue
            if label.lower() in line.lower():
                next_value = _next_nonempty_line(lines, index + 1)
                if next_value and not _line_contains_label(next_value, labels):
                    values.append(next_value)
    return _normalize_list(values)


def _line_contains_label(line: str, labels: Iterable[str]) -> bool:
    lowered = line.lower()
    return any(label.lower() in lowered for label in labels)


def _next_nonempty_line(lines: list[str], start_index: int) -> str | None:
    for line in lines[start_index:]:
        if line:
            return line
    return None


def _scan_for_keywords(lines: list[str], *, keywords: Iterable[str]) -> list[str]:
    results: list[str] = []
    for line in lines:
        lowered = line.lower()
        if any(keyword in lowered for keyword in keywords):
            results.append(line)
    return _normalize_list(results)


def _normalize_list(values: list[str]) -> list[str]:
    cleaned = [value.strip() for value in values if value.strip()]
    cleaned = [value for value in cleaned if not _is_boilerplate_line(value)]
    deduped = []
    seen = set()
    for value in cleaned:
        normalized = value.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(value)
    return deduped


def _infer_exothermicity(section_text: str) -> ExothermicityLevel | None:
    lowered = section_text.lower()
    if "exotherm" in lowered:
        if "violently" in lowered or "kraftigt" in lowered:
            return "high"
        return "medium"
    if "endotherm" in lowered:
        return "none"
    return None


def _is_boilerplate_line(line: str) -> bool:
    return any(pattern.search(line) for pattern in _BOILERPLATE_PATTERNS)
