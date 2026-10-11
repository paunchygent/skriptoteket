"""Gap and segmentation rules judged against real recorded model output and corpus chunks."""

import pytest

from scripts.exam_conversion_eval.gold import GoldExam
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import item_rule_violation
from tests.unit.domain.curated_apps.exam_workspace.source_rules_test_support import (
    FIXTURES,
    chunks_by_anchor,
    item_violations,
    recorded_produced_items,
)


def test_blank_marker_without_gap_or_options_violates_and_other_items_pass():
    violations = item_violations(
        "bf26_diagnostic_grammar_docx_build_response.json",
        "bf26_diagnostic_grammar_test_ht26_med_facit",
    )
    blank_anchors = {"body:0043", "body:0117", "body:0123", "body:0181", "body:0217", "body:0223"}
    flagged = {anchors for anchors, violation in violations.items() if violation is not None}
    assert {a for anchors in flagged for a in anchors} == blank_anchors
    for anchors in flagged:
        assert "blank marker" in (violations[anchors] or "")
    assert len(flagged) == len(blank_anchors)


@pytest.mark.parametrize(
    ("recording", "docx"),
    [
        (
            "svenska_2_grammatik_variant_1_docx_build_response.json",
            "svenska_2_grammatik_omprov_variant_1_med_facit",
        ),
        (
            "svenska_2_grammatik_variant_2_docx_build_response.json",
            "svenska_2_grammatik_omprov_variant_2_med_facit",
        ),
    ],
)
def test_facit_that_splits_units_requires_free_text_and_other_items_pass(recording: str, docx: str):
    violations = item_violations(recording, docx)
    flagged = {anchors[0]: v for anchors, v in violations.items() if v is not None}
    restated = {anchor for anchor, v in flagged.items() if "restates context" in v}
    assert set(flagged) - restated == {"body:0008", "body:0045"}
    assert all("free_text" in flagged[anchor] for anchor in set(flagged) - restated)
    assert len(violations) - len(set(flagged) - restated) == 6


@pytest.mark.parametrize(
    ("recording", "docx"),
    [
        (
            "svenska_2_grammatik_variant_1_docx_build_response.json",
            "svenska_2_grammatik_omprov_variant_1_med_facit",
        ),
        (
            "svenska_2_grammatik_variant_2_docx_build_response.json",
            "svenska_2_grammatik_omprov_variant_2_med_facit",
        ),
    ],
)
def test_gap_for_a_clause_its_line_already_shows_violates_and_gold_gap_counts_follow(
    recording: str, docx: str
):
    """A recorded round gapped the clause each line prints beside its new facit fields."""
    violations = item_violations(recording, docx)
    restated = {anchors for anchors, v in violations.items() if v and "restates context" in v}
    assert len(restated) == 1
    (anchors,) = restated
    gold = GoldExam.model_validate_json((FIXTURES / f"docx_corpus/gold/{docx}.json").read_text())
    gold_item = next(i for i in gold.questions if i.source_label.endswith(" 6"))
    item = next(i for i in recorded_produced_items(recording) if i.source_anchors == anchors)
    gaps = sum(1 for p in item.body for s in p.segments if s.kind == "gap")
    assert gaps > len(gold_item.gaps)


def test_gaps_beyond_blank_markers_violate_as_facit_created_gaps():
    violations = item_violations(
        "bf26_english_1_docx_build_response.json", "bf26_english_1_unit_test_kap_1_2_med_facit"
    )
    flagged = {anchors: v for anchors, v in violations.items() if v is not None}
    assert set(flagged) == {("body:0121",)}
    assert "never creates a gap" in (flagged[("body:0121",)] or "")


@pytest.mark.parametrize(
    ("recording", "docx"),
    [
        (
            "svenska_2_kursavslutande_prov_docx_build_response.json",
            "svenska_2_kursavslutande_prov_med_facit",
        ),
        (
            "sa24_solid_gold_3_docx_build_response_round1.json",
            "sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit",
        ),
        (
            "chapter_4_poetry_docx_build_response.json",
            "chapter_4_poetry_and_lyrics_quiz_med_facit",
        ),
    ],
)
def test_items_whose_gaps_match_source_slots_pass(recording: str, docx: str):
    violations = item_violations(recording, docx)
    assert violations
    assert {anchors: v for anchors, v in violations.items() if v is not None} == {}


def test_review_outcome_never_violates():
    chunks = chunks_by_anchor("svenska_2_grammatik_omprov_variant_1_med_facit")
    item = next(
        item
        for item in recorded_produced_items(
            "svenska_2_grammatik_variant_1_docx_build_response.json"
        )
        if item.source_anchors[0] == "body:0008"
    )
    sources = [chunks[a] for a in item.source_anchors]
    assert item_rule_violation(item, sources) is not None
    review = item.model_copy(update={"outcome": "review", "review_reason": "x"})
    assert item_rule_violation(review, sources) is None
