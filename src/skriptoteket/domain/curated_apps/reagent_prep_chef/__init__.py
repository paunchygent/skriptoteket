"""Domain logic for the curated app: Reagensberedning (Reagent Prep Chef)."""

from .calculator import calculate_numbers
from .errors import ReagentPrepChefErrorCode, rpc_validation_error
from .formulas import (
    molar_mass_g_mol,
    normalize_formula_for_display,
    normalize_formula_key,
)
from .instructions import build_instructions, collect_warnings
from .models import HazardEntry, PrepInputs, PrepNumbers, SafetyResult

__all__ = [
    "HazardEntry",
    "PrepInputs",
    "PrepNumbers",
    "ReagentPrepChefErrorCode",
    "SafetyResult",
    "build_instructions",
    "calculate_numbers",
    "collect_warnings",
    "molar_mass_g_mol",
    "normalize_formula_for_display",
    "normalize_formula_key",
    "rpc_validation_error",
]
