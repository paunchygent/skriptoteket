from __future__ import annotations

import re
from decimal import Decimal

from molmass import Formula

_HYDRATE_DOT_PATTERN = re.compile(r"\.(?=\d)")
_LEADING_INT_PATTERN = re.compile(r"^(?P<count>\d+)(?P<formula>.+)$")


def normalize_formula_key(value: str) -> str:
    normalized = value.strip()
    normalized = normalized.replace("*", "·")
    normalized = _HYDRATE_DOT_PATTERN.sub("·", normalized)
    normalized = re.sub(r"\s+", "", normalized)
    return normalized


def normalize_formula_for_display(formula: str) -> str:
    return normalize_formula_key(formula).replace(".", "·")


def molar_mass_g_mol(*, formula_clean: str) -> Decimal:
    total = Decimal("0")
    for segment in formula_clean.split("·"):
        count, seg_formula = _parse_molar_mass_segment(segment)
        mass = Decimal(str(Formula(seg_formula).mass))
        total += Decimal(count) * mass
    if total <= 0:
        raise ValueError("Invalid formula (molar mass <= 0)")
    return total


def _parse_molar_mass_segment(segment: str) -> tuple[int, str]:
    normalized = segment.strip()
    if not normalized:
        raise ValueError("Empty formula segment")
    match = _LEADING_INT_PATTERN.match(normalized)
    if match is None:
        return 1, normalized
    count = int(match.group("count"))
    if count < 1:
        raise ValueError("Invalid hydrate coefficient")
    return count, match.group("formula")
