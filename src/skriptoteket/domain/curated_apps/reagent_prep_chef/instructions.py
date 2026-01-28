from __future__ import annotations

from decimal import Decimal

from skriptoteket.domain.curated_apps.reagent_prep_chef.formatting import format_decimal
from skriptoteket.domain.curated_apps.reagent_prep_chef.models import PrepNumbers


def collect_warnings(*, numbers: PrepNumbers, min_mass_g: Decimal = Decimal("0.01")) -> list[str]:
    warnings: list[str] = []
    if numbers.mass_g is not None and numbers.mass_g < min_mass_g:
        warnings.append(
            "Beräknad massa är < 0,01 g. Gör en stocklösning först för bättre precision."
        )
    return warnings


def build_instructions(*, numbers: PrepNumbers) -> list[str]:
    if numbers.source_type == "solid":
        if numbers.mass_g is None:
            return []
        mass_g = format_decimal(numbers.mass_g, places=2)
        approx_dissolve_ml = format_decimal(numbers.total_volume_ml * Decimal("0.7"), places=0)
        total_volume_ml = format_decimal(numbers.total_volume_ml, places=1)
        return [
            f"Väg upp {mass_g} g av {numbers.formula_clean}.",
            f"Lös i ca {approx_dissolve_ml} mL destillerat vatten.",
            f"Späd till {total_volume_ml} mL totalt.",
        ]
    if numbers.stock_volume_ml is None or numbers.diluent_volume_ml is None:
        return []
    return [
        f"Mät upp {format_decimal(numbers.stock_volume_ml, places=1)} mL av stocklösningen.",
        f"Tillsätt {format_decimal(numbers.diluent_volume_ml, places=1)} mL vatten.",
        "Blanda väl.",
    ]
