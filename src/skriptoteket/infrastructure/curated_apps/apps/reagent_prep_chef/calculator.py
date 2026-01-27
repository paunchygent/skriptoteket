from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.formulas import (
    molar_mass_g_mol,
    normalize_formula_for_display,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.models import PrepRequest


@dataclass(frozen=True, slots=True)
class PrepNumbers:
    formula_clean: str
    molar_mass_g_mol: Decimal
    total_groups: int
    total_volume_ml: Decimal
    moles_required: Decimal
    source_type: Literal["solid", "liquid_stock"]
    mass_g: Decimal | None = None
    stock_volume_ml: Decimal | None = None
    diluent_volume_ml: Decimal | None = None


def calculate_numbers(*, request: PrepRequest) -> PrepNumbers:
    formula_clean = normalize_formula_for_display(request.chemical_formula)
    molar_mass = molar_mass_g_mol(formula_clean=formula_clean)

    total_groups = _ceil_div(request.student_count, request.students_per_group)
    base_total_volume_ml = request.vol_per_group_ml * Decimal(total_groups)
    total_volume_ml = base_total_volume_ml * (Decimal("1") + request.safety_factor)
    moles_required = request.target_molarity * (total_volume_ml / Decimal("1000"))

    if request.source_type == "solid":
        mass_g = (moles_required * molar_mass) / request.solute_purity
        return PrepNumbers(
            formula_clean=formula_clean,
            molar_mass_g_mol=molar_mass,
            total_groups=total_groups,
            total_volume_ml=total_volume_ml,
            moles_required=moles_required,
            source_type=request.source_type,
            mass_g=mass_g,
        )

    stock_molarity = request.stock_molarity
    if stock_molarity is None:
        raise ValueError("stock_molarity is required when source_type=liquid_stock")

    stock_volume_ml = (moles_required / stock_molarity) * Decimal("1000")
    diluent_volume_ml = total_volume_ml - stock_volume_ml
    return PrepNumbers(
        formula_clean=formula_clean,
        molar_mass_g_mol=molar_mass,
        total_groups=total_groups,
        total_volume_ml=total_volume_ml,
        moles_required=moles_required,
        source_type=request.source_type,
        stock_volume_ml=stock_volume_ml,
        diluent_volume_ml=diluent_volume_ml,
    )


def _ceil_div(a: int, b: int) -> int:
    return (a + b - 1) // b
