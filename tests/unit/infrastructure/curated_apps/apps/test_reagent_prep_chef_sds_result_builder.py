from __future__ import annotations

from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_result_builder import (
    GhsSnapshot,
    merge_pdf_ghs,
)


def test_merge_pdf_ghs_unions_hazards_and_prefers_danger() -> None:
    snapshot = GhsSnapshot(
        hazard_codes=["H319"],
        pictograms=["GHS07"],
        signal_word="warning",
        nonhazardous=False,
        sources=[],
    )
    pdf_text = """
    Safety Data Sheet
    Signal word: Danger
    H335 H372
    GHS08
    """

    merged = merge_pdf_ghs(snapshot=snapshot, pdf_text=pdf_text)

    assert merged.hazard_codes == ["H319", "H335", "H372"]
    assert merged.pictograms == ["GHS07", "GHS08"]
    assert merged.signal_word == "danger"


def test_merge_pdf_ghs_clears_nonhazardous_on_pdf_hazards() -> None:
    snapshot = GhsSnapshot(
        hazard_codes=[],
        pictograms=[],
        signal_word=None,
        nonhazardous=True,
        sources=[],
    )
    pdf_text = "Safety Data Sheet\nH319"

    merged = merge_pdf_ghs(snapshot=snapshot, pdf_text=pdf_text)

    assert merged.nonhazardous is False
