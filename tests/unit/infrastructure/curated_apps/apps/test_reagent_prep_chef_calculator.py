from __future__ import annotations

from decimal import Decimal

from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.calculator import (
    calculate_numbers,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.models import PrepRequest


def test_calculate_numbers_for_solid_solution() -> None:
    request = PrepRequest(
        chemical_formula="NaCl",
        target_molarity="0.1",
        vol_per_group_ml="50",
        student_count=30,
        students_per_group=2,
        safety_factor="0.10",
        source_type="solid",
        solute_purity="1.0",
    )

    numbers = calculate_numbers(request=request)

    assert numbers.total_groups == 15
    assert numbers.total_volume_ml == Decimal("825.0")
    assert numbers.moles_required == Decimal("0.0825")
    assert numbers.mass_g is not None
    assert Decimal("4.7") <= numbers.mass_g <= Decimal("4.9")


def test_calculate_numbers_for_dilution() -> None:
    request = PrepRequest(
        chemical_formula="NaCl",
        target_molarity="0.1",
        vol_per_group_ml="50",
        student_count=30,
        students_per_group=2,
        safety_factor="0.10",
        source_type="liquid_stock",
        stock_molarity="1.0",
        solute_purity="1.0",
    )

    numbers = calculate_numbers(request=request)

    assert numbers.total_groups == 15
    assert numbers.total_volume_ml == Decimal("825.0")
    assert numbers.stock_volume_ml == Decimal("82.5")
    assert numbers.diluent_volume_ml == Decimal("742.5")
