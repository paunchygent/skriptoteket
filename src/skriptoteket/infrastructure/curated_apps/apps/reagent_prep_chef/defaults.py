from __future__ import annotations

from pydantic import JsonValue


def default_inputs() -> dict[str, JsonValue]:
    return {
        "chemical_formula": "",
        "target_molarity": "0.1",
        "vol_per_group_ml": "50",
        "student_count": 30,
        "students_per_group": 2,
        "safety_factor": "0.10",
        "source_type": "solid",
        "solute_purity": "1.0",
    }
