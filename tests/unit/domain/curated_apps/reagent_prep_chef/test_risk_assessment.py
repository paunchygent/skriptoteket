from __future__ import annotations

from skriptoteket.domain.curated_apps.reagent_prep_chef.risk_assessment import (
    RiskTemplate,
    filter_templates_by_hazard_codes,
)


def test_filter_templates_by_hazard_codes_matches_any() -> None:
    templates = [
        RiskTemplate(
            id="eye_contact",
            title="Stänk i ögon",
            hazard_codes_any=("H314", "H318", "H319"),
        ),
        RiskTemplate(
            id="generic",
            title="Allmänt",
            hazard_codes_any=(),
        ),
    ]

    matched = filter_templates_by_hazard_codes(templates=templates, hazard_codes={"H318"})
    assert [item.id for item in matched] == ["eye_contact"]
