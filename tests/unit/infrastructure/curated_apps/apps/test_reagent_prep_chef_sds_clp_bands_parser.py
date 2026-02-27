"""Tests for CLP band parsing from SDS text.

These tests pin real-world failure modes seen in PR-0062 Slice 6.x:

- Some SDS documents place "Specific concentration limits" (SCL) in Section 3 rather than Section 2.
- SCL lines can include the CLP-style `C ≥ 15 %` / `5 % ≤ C < 15 %` syntax.

The parser must extract bands from the correct section without relying on external heuristics.
"""

from __future__ import annotations

from decimal import Decimal

from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers.clp_bands import (
    parse_sds_clp_bands_from_text,
)


def test_parse_sds_clp_bands_falls_back_to_section_3_when_section_2_has_no_bands() -> None:
    # This mirrors the Carl Roth H2SO4 SDS shape:
    # - Section 2 has hazard classification but no concentration limits.
    # - Section 3 contains a "Specific Conc. Limits" table with CLP SCL notation.
    text = "\n".join(
        [
            "Safety data sheet",
            "Section 2: Hazards identification",
            "Met. Corr. 1 H290",
            "Skin Corr. 1A H314",
            "Eye Dam. 1 H318",
            "Section 3: Composition/information on ingredients",
            "Substance, Specific Conc. Limits, M-factors, ATE",
            "Skin Corr. 1A; H314: C ≥ 15 %",
            "Skin Irrit. 2; H315: 5 % ≤ C < 15 %",
            "Eye Dam. 1; H318: C ≥ 15 %",
            "Eye Irrit. 2; H319: 5 % ≤ C < 15 %",
            "Section 4: First aid measures",
        ]
    )

    bands = parse_sds_clp_bands_from_text(
        text,
        molar_mass_g_mol=Decimal("98.07"),
        density_g_ml=Decimal("1.0"),
    )

    assert {code for band in bands for code in band.hazard_codes} >= {
        "H314",
        "H315",
        "H318",
        "H319",
    }
    assert any(band.min_molarity is not None for band in bands)
    assert any(band.max_molarity is not None for band in bands)
