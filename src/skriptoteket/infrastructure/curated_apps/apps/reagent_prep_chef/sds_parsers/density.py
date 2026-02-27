"""Density parsing for SDS PDF text in Reagent Prep Chef.

PubChem density is missing for many compounds. When an SDS PDF is available, Section 9
often contains explicit density lines that can be parsed deterministically (no guessing).

This module provides a small, unit-normalizing extractor that converts common density
units into g/mL so downstream CLP band conversion can proceed.

Related:
  - `sds_parsers/pdf_text.py` (PDF → text)
  - `sds_parsers/sections.py` (Section 9 extraction)
  - `sds_fetcher.py` (uses density for CLP band derivation)
"""

from __future__ import annotations

import re
from decimal import Decimal

from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers.pdf_text import (
    extract_pdf_text,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers.sections import (
    extract_section,
)

_DENSITY_UNIT_RE = re.compile(
    r"(?P<value>\d+(?:[.,]\d+)?)\s*(?P<unit>"
    r"g\s*/\s*(?:cm3|cm\^3|cm³|cu\s*cm|cc|ml|mL|l|L)"
    r"|kg\s*/\s*(?:m3|m\^3|m³)"
    r")",
    re.IGNORECASE,
)
_RELATIVE_DENSITY_RE = re.compile(r"\b(relative density|specific gravity)\b", re.IGNORECASE)
_VAPOUR_DENSITY_RE = re.compile(r"\b(vapou?r density|relative vapou?r density)\b", re.IGNORECASE)
_DECIMAL_VALUE_RE = re.compile(r"\d+(?:[.,]\d+)?")


def extract_density_g_ml_from_pdf_bytes(pdf_bytes: bytes) -> Decimal | None:
    """Extract density (g/mL) from a PDF SDS document."""
    text = extract_pdf_text(pdf_bytes)
    return extract_density_g_ml_from_sds_text(text)


def extract_density_g_ml_from_sds_text(text: str) -> Decimal | None:
    """Extract density (g/mL) from SDS text (Section 9 preferred)."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    section_text = extract_section(lines, section_number="9")
    candidates = section_text.splitlines() if section_text else lines

    for raw_line in candidates:
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        if "density" not in lowered and "gravity" not in lowered:
            continue
        if _VAPOUR_DENSITY_RE.search(lowered):
            continue

        unit_match = _DENSITY_UNIT_RE.search(line)
        if unit_match:
            value = _decimal_from_text(unit_match.group("value"))
            if value is None:
                continue
            unit = re.sub(r"\s+", "", unit_match.group("unit")).lower().replace("³", "3")
            if unit in {"g/cm3", "g/cm^3", "g/cucm", "g/cc", "g/ml"}:
                return value
            if unit in {"kg/m3", "kg/m^3"}:
                return (value / Decimal("1000")).quantize(Decimal("0.000001"))
            if unit in {"g/l"}:
                return (value / Decimal("1000")).quantize(Decimal("0.000001"))
            continue

        if _RELATIVE_DENSITY_RE.search(lowered):
            number = _DECIMAL_VALUE_RE.search(line)
            if number:
                value = _decimal_from_text(number.group(0))
                if value is not None:
                    return value

    return None


def _decimal_from_text(value: str) -> Decimal | None:
    cleaned = value.strip().replace(",", ".")
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except Exception:
        return None
