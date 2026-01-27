from __future__ import annotations

from decimal import Decimal

import pytest

from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.formulas import (
    molar_mass_g_mol,
    normalize_formula_key,
)


def test_normalize_formula_key_handles_common_hydrate_separators() -> None:
    assert normalize_formula_key("CuSO4.5H2O") == "CuSO4·5H2O"
    assert normalize_formula_key("CuSO4*5H2O") == "CuSO4·5H2O"
    assert normalize_formula_key(" CuSO4 · 5H2O ") == "CuSO4·5H2O"


def test_molar_mass_g_mol_handles_hydrates() -> None:
    mass = molar_mass_g_mol(formula_clean="CuSO4·5H2O")
    assert Decimal("249.60") <= mass <= Decimal("249.80")


def test_molar_mass_g_mol_rejects_invalid_formulas() -> None:
    with pytest.raises(ValueError):
        molar_mass_g_mol(formula_clean="not a formula")
