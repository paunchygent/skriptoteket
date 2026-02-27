"""Tests for SDS PDF-text density extraction in Reagent Prep Chef.

These tests pin the behavior of the PDF-text density fallback used when PubChem density
is missing for a compound but the SDS PDF includes explicit density lines (typically in
Section 9).

Related:
  - `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/sds_parsers/density.py`
  - `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/sds_fetcher.py`
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers import (
    extract_density_g_ml_from_sds_text,
)


def test_extract_density_g_ml_from_sds_text_prefers_section_9_density_line() -> None:
    text = """Safety Data Sheet
Section 9: Physical and chemical properties
Relative vapour density at 20°C : 6.31
Density : 6.31 g/cm³
Section 10: Stability and reactivity
"""
    assert extract_density_g_ml_from_sds_text(text) == Decimal("6.31")


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("Density : 2.2 g/cm³", Decimal("2.2")),
        ("Density 2.15 g/cu cm at 25 °C", Decimal("2.15")),
        ("Density: 1000 kg/m³", Decimal("1.000000")),
        ("Density: 1000 g/L", Decimal("1.000000")),
    ],
)
def test_extract_density_g_ml_from_sds_text_parses_common_units(
    line: str, expected: Decimal
) -> None:
    text = """Safety Data Sheet
Section 9: Physical and chemical properties
{line}
Section 10: Stability and reactivity
""".format(line=line)
    assert extract_density_g_ml_from_sds_text(text) == expected


def test_extract_density_g_ml_from_sds_text_accepts_relative_density_as_fallback() -> None:
    text = """Safety Data Sheet
Section 9: Physical and chemical properties
Relative density : 1.234
Section 10: Stability and reactivity
"""
    assert extract_density_g_ml_from_sds_text(text) == Decimal("1.234")
