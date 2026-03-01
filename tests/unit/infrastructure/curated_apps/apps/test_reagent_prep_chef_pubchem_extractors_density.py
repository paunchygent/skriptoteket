"""Tests for PubChem density parsing in Reagent Prep Chef SDS derivation.

These tests validate `extract_density_g_ml` against real-world unit variants seen in
PubChem PUG-View "Density" sections (unicode superscripts, g/cu cm, kg/m³, g/L).

Related:
  - `infrastructure/curated_apps/apps/reagent_prep_chef/sds_parsers/pubchem_extractors.py`
  - `infrastructure/curated_apps/apps/reagent_prep_chef/sds_fetcher.py`
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers import (
    extract_density_g_ml,
)


def _payload_for_density_lines(*lines: str) -> dict:
    return {
        "Record": {
            "Section": [
                {
                    "TOCHeading": "Density",
                    "Information": [
                        {
                            "Name": "Density",
                            "Value": {
                                "StringWithMarkup": [{"String": "\n".join(lines), "Markup": []}],
                            },
                        }
                    ],
                }
            ]
        }
    }


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("Density (at 25 °C): 2.2 g/cm³", Decimal("2.2")),
        ("2.15 g/cu cm at 25 °C", Decimal("2.15")),
        ("1.03 g/mL at 20 °C", Decimal("1.03")),
        ("1000 kg/m³", Decimal("1.000000")),
        ("1000 g/L", Decimal("1.000000")),
    ],
)
def test_extract_density_g_ml_parses_common_units(line: str, expected: Decimal) -> None:
    payload = _payload_for_density_lines(line)
    assert extract_density_g_ml(payload) == expected


def test_extract_density_g_ml_accepts_relative_density_as_specific_gravity() -> None:
    payload = _payload_for_density_lines("Relative density: 1.234")
    assert extract_density_g_ml(payload) == Decimal("1.234")
