from __future__ import annotations

from skriptoteket.domain.curated_apps.reagent_prep_chef.risk_assessment import (
    DEFAULT_RISK_LEVELS,
    resolve_risk_level,
    score_risk,
)


def test_risk_scoring_and_level_resolution() -> None:
    score = score_risk(severity=2, likelihood=3)
    assert score == 6
    assert resolve_risk_level(score=score, levels=DEFAULT_RISK_LEVELS) == "medium"
