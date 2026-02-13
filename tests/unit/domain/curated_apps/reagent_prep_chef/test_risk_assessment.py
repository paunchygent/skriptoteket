from __future__ import annotations

from decimal import Decimal

from skriptoteket.domain.curated_apps.reagent_prep_chef.models import ClpBand
from skriptoteket.domain.curated_apps.reagent_prep_chef.risk_assessment import (
    DEFAULT_RISK_LEVELS,
    resolve_risk_level,
    score_risk,
    select_clp_band,
)


def test_risk_scoring_and_level_resolution() -> None:
    score = score_risk(severity=2, likelihood=3)
    assert score == 6
    assert resolve_risk_level(score=score, levels=DEFAULT_RISK_LEVELS) == "medium"


def test_select_clp_band_merges_overlapping_hazards() -> None:
    bands = [
        ClpBand(
            min_molarity=Decimal("0.1"),
            max_molarity=Decimal("1.0"),
            hazard_codes=("H319",),
            pictograms=("GHS07",),
            signal_word="warning",
            notes=("note-a",),
        ),
        ClpBand(
            min_molarity=Decimal("0.2"),
            max_molarity=Decimal("1.0"),
            hazard_codes=("H335",),
            pictograms=("GHS08",),
            signal_word="danger",
            notes=("note-b",),
        ),
    ]

    selected = select_clp_band(bands=bands, molarity=Decimal("0.5"))

    assert selected is not None
    assert selected.hazard_codes == ("H319", "H335")
    assert selected.pictograms == ("GHS07", "GHS08")
    assert selected.signal_word == "danger"
    assert selected.min_molarity == Decimal("0.2")
    assert selected.max_molarity == Decimal("1.0")
    assert selected.notes == ("note-a", "note-b")
