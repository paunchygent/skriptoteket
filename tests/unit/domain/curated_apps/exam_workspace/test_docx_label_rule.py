"""The label rule judged against real recorded model output: printed numbers and points stay out."""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import label_rule_violation
from tests.unit.domain.curated_apps.exam_workspace.source_rules_test_support import (
    chunks_by_anchor,
    recorded_produced_items,
)

_ENGLISH = "bf26_english_1_unit_test_kap_1_2_med_facit"
_METHOD = "metodprov_vetenskaplig_metod_med_facit"
_POETRY = "chapter_4_poetry_and_lyrics_quiz_med_facit"
_GRAMMAR = "svenska_2_grammatik_omprov_variant_1_med_facit"


def _violations(version: str, docx: str) -> dict[str, str]:
    chunks = chunks_by_anchor(docx)
    items = recorded_produced_items(f"docx_build_{version}/{docx}/round1.json")
    return {
        item.source_anchors[0]: violation
        for item in items
        if (violation := label_rule_violation(item, [chunks[a] for a in item.source_anchors]))
    }


def _item(version: str, docx: str, anchor: str) -> ProducedItem:
    items = recorded_produced_items(f"docx_build_{version}/{docx}/round1.json")
    return next(item for item in items if item.source_anchors[0] == anchor)


@pytest.mark.parametrize(
    ("docx", "count"),
    [(_METHOD, 16), (_GRAMMAR, 7), ("svenska_2_kursavslutande_prov_med_facit", 9)],
)
def test_items_that_keep_their_printed_question_number_violate(docx: str, count: int):
    flagged = _violations("v5", docx)

    assert len(flagged) == count
    for anchor, violation in flagged.items():
        assert f"question number that {anchor} prints" in violation


def test_numbered_items_among_unnumbered_ones_name_only_the_numbered_items():
    assert list(_violations("v5", _ENGLISH)) == ["body:0059", "body:0063", "body:0067"]


def test_items_that_keep_a_printed_points_label_violate():
    flagged = _violations("v5", _POETRY)

    assert len(flagged) == 20
    assert all(f"points label that {anchor} shows" in v for anchor, v in flagged.items())
    assert "body:0032" in flagged and "body:0147" in flagged


@pytest.mark.parametrize("version", ["v6", "v7"])
@pytest.mark.parametrize(
    "docx",
    [
        _ENGLISH,
        _METHOD,
        _POETRY,
        _GRAMMAR,
        "bf26_diagnostic_grammar_test_ht26_med_facit",
        "sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit",
        "svenska_2_grammatik_omprov_variant_2_med_facit",
        "svenska_2_kursavslutande_prov_med_facit",
    ],
)
def test_items_that_dropped_their_labels_pass_in_the_current_recordings(version: str, docx: str):
    assert _violations(version, docx) == {}


def test_removing_the_printed_number_from_a_violating_item_clears_it():
    docx, anchor = _METHOD, "body:0005"
    item = _item("v5", docx, anchor)
    chunks = [chunks_by_anchor(docx)[a] for a in item.source_anchors]
    assert label_rule_violation(item, chunks) is not None
    assert item.title is not None and item.title.startswith("1.")
    assert item.title.endswith("(1 poäng)")

    number_only = item.model_copy(update={"title": item.title.removeprefix("1.").strip()})
    clean = item.model_copy(
        update={"title": item.title.removeprefix("1.").removesuffix("(1 poäng)").strip()}
    )

    # The printed points label is a second violation of the same item.
    violation = label_rule_violation(number_only, chunks)
    assert violation is not None and "points label that body:0005 shows" in violation
    assert label_rule_violation(clean, chunks) is None


def test_part_label_and_numerals_of_the_wording_are_no_question_number():
    chunks = chunks_by_anchor(_POETRY)
    part = _item("v7", _POETRY, "body:0111")
    assert part.title == "Part 3" and chunks["body:0111"].text.startswith("Part 3, Question")
    assert label_rule_violation(part, [chunks[a] for a in part.source_anchors]) is None

    method = chunks_by_anchor(_METHOD)
    numeral = _item("v7", _METHOD, "body:0061")
    assert numeral.title == "20 eller 200 elever"
    assert label_rule_violation(numeral, [method[a] for a in numeral.source_anchors]) is None


def test_points_label_added_to_a_clean_item_violates():
    chunks = chunks_by_anchor(_POETRY)
    item = _item("v7", _POETRY, "body:0032")
    sources = [chunks[a] for a in item.source_anchors]
    assert "(1 point)" in chunks["body:0032"].text
    assert label_rule_violation(item, sources) is None

    labelled = item.model_copy(update={"title": f"{item.title} (1 point)"})

    violation = label_rule_violation(labelled, sources)
    assert violation is not None and "points label that body:0032 shows" in violation


def test_sentence_wording_about_points_is_no_points_label():
    chunks = chunks_by_anchor(_ENGLISH)
    sentence = "Each correct match is worth 1 point."
    assert sentence in chunks["body:0058"].text
    item = _item("v7", _ENGLISH, "body:0059")
    assert sentence in " ".join(
        s.text or "" for p in item.body for s in p.segments if s.kind == "text"
    )

    # Even when the instruction chunk is the item's own source, its sentence is question text.
    assert label_rule_violation(item, [chunks["body:0058"], chunks["body:0059"]]) is None


def test_review_outcome_never_violates():
    docx = _METHOD
    item = _item("v5", docx, "body:0005")
    chunks = [chunks_by_anchor(docx)[a] for a in item.source_anchors]
    review = item.model_copy(update={"outcome": "review", "review_reason": "x"})

    assert label_rule_violation(item, chunks) is not None
    assert label_rule_violation(review, chunks) is None


_DIAGNOSTIC = "bf26_diagnostic_grammar_test_ht26_med_facit"
_LEGACY_DIAGNOSTIC = "bf26_diagnostic_grammar_docx_build_response.json"
_SOLID_GOLD = "sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit"


def test_free_text_item_that_keeps_its_printed_blank_marker_violates():
    chunks = chunks_by_anchor(_DIAGNOSTIC)
    recorded = recorded_produced_items(_LEGACY_DIAGNOSTIC)
    item = next(i for i in recorded if i.source_anchors == ("body:0043",))
    assert item.kind.value == "free_text"
    assert any("____" in (s.text or "") for p in item.body for s in p.segments)

    violation = label_rule_violation(item, [chunks[a] for a in item.source_anchors])

    assert violation is not None and "blank marker" in violation


def test_blank_marker_added_to_a_clean_item_of_any_non_choice_kind_violates():
    chunks = chunks_by_anchor(_DIAGNOSTIC)
    items = recorded_produced_items(f"docx_build_v7/{_DIAGNOSTIC}/round1.json")
    clean = [i for i in items if i.kind.value in ("free_text", "gap_fill") and i.body]
    assert clean
    for item in clean:
        sources = [chunks[a] for a in item.source_anchors]
        assert label_rule_violation(item, sources) is None
        first = item.body[0]
        text = first.segments[0].model_copy(update={"text": f"{first.segments[0].text} ____"})
        marked = item.model_copy(
            update={
                "body": (
                    first.model_copy(update={"segments": (text, *first.segments[1:])}),
                    *item.body[1:],
                )
            }
        )
        violation = label_rule_violation(marked, sources)
        assert violation is not None and "blank marker" in violation


def test_choice_item_prompt_keeps_its_response_position_but_its_options_do_not():
    chunks = chunks_by_anchor(_SOLID_GOLD)
    item = _item("v7", _SOLID_GOLD, "body:0004")
    sources = [chunks[a] for a in item.source_anchors]
    assert item.kind.value == "single_choice"
    assert "___" in (item.body[0].segments[0].text or "")
    assert label_rule_violation(item, sources) is None

    first = item.choices[0]
    marked = item.model_copy(
        update={
            "choices": (first.model_copy(update={"text": f"{first.text} ___"}), *item.choices[1:])
        }
    )

    violation = label_rule_violation(marked, sources)
    assert violation is not None and "blank marker" in violation
