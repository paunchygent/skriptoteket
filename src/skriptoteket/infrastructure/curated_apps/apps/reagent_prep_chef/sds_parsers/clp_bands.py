from __future__ import annotations

import re
from decimal import Decimal

from skriptoteket.domain.curated_apps.reagent_prep_chef.models import ClpBand
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers.patterns import (
    HAZARD_CODE_RE,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers.sections import (
    extract_section,
)

_PERCENT_RANGE_RE = re.compile(
    r"(?P<min>\d+(?:[.,]\d+)?)\s*%?\s*(?:≤|<=|<)\s*C\s*"
    r"(?:<|≤|<=)\s*(?P<max>\d+(?:[.,]\d+)?)\s*%",
    re.IGNORECASE,
)
_PERCENT_MIN_RE = re.compile(
    r"C\s*(?:≥|>=|>)\s*(?P<min>\d+(?:[.,]\d+)?)\s*%",
    re.IGNORECASE,
)
_PERCENT_MAX_RE = re.compile(
    r"C\s*(?:≤|<=|<)\s*(?P<max>\d+(?:[.,]\d+)?)\s*%",
    re.IGNORECASE,
)
_PERCENT_RANGE_ALT_RE = re.compile(
    r"(?P<min>\d+(?:[.,]\d+)?)\s*%\s*(?:-|–|to)\s*(?P<max>\d+(?:[.,]\d+)?)\s*%",
    re.IGNORECASE,
)
_MOLAR_RANGE_RE = re.compile(
    r"(?P<min>\d+(?:[.,]\d+)?)\s*(?:mol/L|M)\s*(?:≤|<=|<)\s*C\s*"
    r"(?:<|≤|<=)\s*(?P<max>\d+(?:[.,]\d+)?)\s*(?:mol/L|M)",
    re.IGNORECASE,
)
_MOLAR_MIN_RE = re.compile(
    r"C\s*(?:≥|>=|>)\s*(?P<min>\d+(?:[.,]\d+)?)\s*(?:mol/L|M)",
    re.IGNORECASE,
)
_MOLAR_MAX_RE = re.compile(
    r"C\s*(?:≤|<=|<)\s*(?P<max>\d+(?:[.,]\d+)?)\s*(?:mol/L|M)",
    re.IGNORECASE,
)
_MASS_RANGE_RE = re.compile(
    r"(?P<min>\d+(?:[.,]\d+)?)\s*(?P<unit>mg/L|g/L)\s*(?:≤|<=|<)\s*C\s*"
    r"(?:<|≤|<=)\s*(?P<max>\d+(?:[.,]\d+)?)\s*(?P=unit)",
    re.IGNORECASE,
)
_MASS_MIN_RE = re.compile(
    r"C\s*(?:≥|>=|>)\s*(?P<min>\d+(?:[.,]\d+)?)\s*(?P<unit>mg/L|g/L)",
    re.IGNORECASE,
)
_MASS_MAX_RE = re.compile(
    r"C\s*(?:≤|<=|<)\s*(?P<max>\d+(?:[.,]\d+)?)\s*(?P<unit>mg/L|g/L)",
    re.IGNORECASE,
)


def parse_sds_clp_bands_from_text(
    text: str,
    *,
    molar_mass_g_mol: Decimal,
    density_g_ml: Decimal,
) -> list[ClpBand]:
    """Parse concentration-dependent CLP bands from SDS text."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    section_text = extract_section(lines, section_number="2")
    if not section_text:
        section_text = extract_section(lines, section_number="3")
    if not section_text:
        return []
    target_lines = [line.strip() for line in section_text.splitlines() if line.strip()]

    bands: list[ClpBand] = []
    for line in target_lines:
        hazard_codes = HAZARD_CODE_RE.findall(line)
        if not hazard_codes:
            continue
        band = _parse_concentration_band(
            line=line,
            hazard_codes=hazard_codes,
            molar_mass_g_mol=molar_mass_g_mol,
            density_g_ml=density_g_ml,
        )
        if band is not None:
            bands.append(band)

    return _dedupe_bands(bands)


def _parse_concentration_band(
    *,
    line: str,
    hazard_codes: list[str],
    molar_mass_g_mol: Decimal,
    density_g_ml: Decimal,
) -> ClpBand | None:
    unique_codes = tuple(sorted({code.upper() for code in hazard_codes}))
    if not unique_codes:
        return None

    percent_bounds = _extract_percent_bounds(line)
    if percent_bounds is not None:
        basis = _extract_percent_basis(line)
        if basis is None:
            return None
        min_molarity = _percent_to_molarity(
            percent_bounds[0],
            molar_mass_g_mol=molar_mass_g_mol,
            density_g_ml=density_g_ml,
            basis=basis,
        )
        max_molarity = _percent_to_molarity(
            percent_bounds[1],
            molar_mass_g_mol=molar_mass_g_mol,
            density_g_ml=density_g_ml,
            basis=basis,
        )
        if min_molarity is None and max_molarity is None:
            return None
        return ClpBand(
            min_molarity=min_molarity,
            max_molarity=max_molarity,
            hazard_codes=unique_codes,
            pictograms=(),
            signal_word=None,
            notes=(),
        )

    molar_bounds = _extract_molar_bounds(line)
    if molar_bounds is not None:
        return ClpBand(
            min_molarity=molar_bounds[0],
            max_molarity=molar_bounds[1],
            hazard_codes=unique_codes,
            pictograms=(),
            signal_word=None,
            notes=(),
        )

    mass_bounds = _extract_mass_bounds(line)
    if mass_bounds is not None:
        min_molarity = _mass_to_molarity(
            mass_bounds[0], unit=mass_bounds[2], molar_mass_g_mol=molar_mass_g_mol
        )
        max_molarity = _mass_to_molarity(
            mass_bounds[1], unit=mass_bounds[2], molar_mass_g_mol=molar_mass_g_mol
        )
        if min_molarity is None and max_molarity is None:
            return None
        return ClpBand(
            min_molarity=min_molarity,
            max_molarity=max_molarity,
            hazard_codes=unique_codes,
            pictograms=(),
            signal_word=None,
            notes=(),
        )

    return None


def _extract_percent_bounds(line: str) -> tuple[Decimal | None, Decimal | None] | None:
    match = _PERCENT_RANGE_RE.search(line) or _PERCENT_RANGE_ALT_RE.search(line)
    if match:
        return (_decimal_from_text(match.group("min")), _decimal_from_text(match.group("max")))

    match = _PERCENT_MIN_RE.search(line)
    if match:
        return (_decimal_from_text(match.group("min")), None)

    match = _PERCENT_MAX_RE.search(line)
    if match:
        return (None, _decimal_from_text(match.group("max")))

    return None


def _extract_molar_bounds(line: str) -> tuple[Decimal | None, Decimal | None] | None:
    match = _MOLAR_RANGE_RE.search(line)
    if match:
        return (_decimal_from_text(match.group("min")), _decimal_from_text(match.group("max")))
    match = _MOLAR_MIN_RE.search(line)
    if match:
        return (_decimal_from_text(match.group("min")), None)
    match = _MOLAR_MAX_RE.search(line)
    if match:
        return (None, _decimal_from_text(match.group("max")))
    return None


def _extract_mass_bounds(
    line: str,
) -> tuple[Decimal | None, Decimal | None, str] | None:
    match = _MASS_RANGE_RE.search(line)
    if match:
        return (
            _decimal_from_text(match.group("min")),
            _decimal_from_text(match.group("max")),
            match.group("unit"),
        )
    match = _MASS_MIN_RE.search(line)
    if match:
        return (_decimal_from_text(match.group("min")), None, match.group("unit"))
    match = _MASS_MAX_RE.search(line)
    if match:
        return (None, _decimal_from_text(match.group("max")), match.group("unit"))
    return None


def _extract_percent_basis(line: str) -> str | None:
    lowered = line.lower()
    if "w/w" in lowered or "wt%" in lowered or "weight %" in lowered or "mass %" in lowered:
        return "w/w"
    if "w/v" in lowered:
        return "w/v"
    if "v/v" in lowered:
        return "v/v"
    return None


def _percent_to_molarity(
    value: Decimal | None,
    *,
    molar_mass_g_mol: Decimal,
    density_g_ml: Decimal,
    basis: str,
) -> Decimal | None:
    if value is None:
        return None
    if molar_mass_g_mol <= 0:
        return None
    if density_g_ml <= 0:
        return None
    fraction = value / Decimal("100")
    if basis == "w/w":
        g_per_l = fraction * density_g_ml * Decimal("1000")
    elif basis == "w/v":
        g_per_l = value * Decimal("10")
    elif basis == "v/v":
        g_per_l = fraction * density_g_ml * Decimal("1000")
    else:
        return None
    return _mass_to_molarity(g_per_l, unit="g/L", molar_mass_g_mol=molar_mass_g_mol)


def _mass_to_molarity(
    value: Decimal | None,
    *,
    unit: str,
    molar_mass_g_mol: Decimal,
) -> Decimal | None:
    if value is None:
        return None
    if molar_mass_g_mol <= 0:
        return None
    normalized = unit.lower()
    grams = value
    if normalized == "mg/l":
        grams = value / Decimal("1000")
    elif normalized == "g/l":
        grams = value
    return grams / molar_mass_g_mol


def _decimal_from_text(value: str) -> Decimal | None:
    cleaned = value.strip().replace(",", ".")
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except Exception:
        return None


def _dedupe_bands(bands: list[ClpBand]) -> list[ClpBand]:
    seen: set[tuple[Decimal | None, Decimal | None, tuple[str, ...]]] = set()
    ordered: list[ClpBand] = []
    for band in bands:
        key = (band.min_molarity, band.max_molarity, band.hazard_codes)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(band)
    return ordered
