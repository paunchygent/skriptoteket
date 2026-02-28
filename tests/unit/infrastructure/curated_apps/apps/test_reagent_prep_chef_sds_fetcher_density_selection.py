"""Unit tests for density source selection in the Reagent Prep Chef SDS fetch pipeline.

This pins a real failure mode found in PR-0062 Slice 6.8:

- PubChem density for gas-phase compounds (e.g. HCl/HF) can be present but irrelevant to the
  aqueous stock solution described by the SDS PDF.
- If the SDS PDF contains a Section 9 density line, the fetcher must prefer that value so CLP
  band molarity conversion uses the correct density.
"""

from __future__ import annotations

from decimal import Decimal

from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_fetcher import (
    _select_density_g_ml,
)


def test_select_density_prefers_pdf_over_pubchem() -> None:
    density, source = _select_density_g_ml(
        pubchem_density_g_ml=Decimal("0.001639"),
        pdf_density_g_ml=Decimal("1.19"),
    )

    assert source == "pdf"
    assert density == Decimal("1.19")


def test_select_density_falls_back_to_pubchem_when_pdf_missing() -> None:
    density, source = _select_density_g_ml(
        pubchem_density_g_ml=Decimal("1.84"),
        pdf_density_g_ml=None,
    )

    assert source == "pubchem"
    assert density == Decimal("1.84")


def test_select_density_reports_missing_when_both_missing() -> None:
    density, source = _select_density_g_ml(
        pubchem_density_g_ml=None,
        pdf_density_g_ml=None,
    )

    assert source == "missing"
    assert density is None
