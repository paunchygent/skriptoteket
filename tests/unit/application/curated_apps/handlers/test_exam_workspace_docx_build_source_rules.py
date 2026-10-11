"""Batch admission enforces source-structure rules on real recorded model output."""

import json
from pathlib import Path
from uuid import uuid4

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)

_FIXTURES = Path("tests/fixtures/exam_conversion")


def _admitted(recording: str, docx: str) -> DocxBuildState:
    chunks = PythonDocxExamChunker().chunk(
        content=(_FIXTURES / f"docx_corpus/{docx}.docx").read_bytes()
    )
    state = DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename="test.docx",
        source_sha256="a" * 64,
        chunks=chunks,
    )
    admit_batch(json.loads((_FIXTURES / recording).read_text()), state)
    return state


def test_opening_heading_listed_as_facit_stays_pending_for_the_title():
    state = _admitted(
        "sa24_solid_gold_3_docx_build_response_round1.json",
        "sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit",
    )
    assert "body:0002" not in state.key_anchors
    assert "body:0002" not in state.claimed
    assert "body:0002" in {chunk.anchor for chunk in state.pending}
    assert len([f for f in state.failures if "opening heading" in f]) == 1
    assert any(event.code == "answer_key_source_rule" for event in state.events)


def test_items_breaking_unit_segmentation_rule_are_rejected_and_stay_pending():
    state = _admitted(
        "svenska_2_grammatik_variant_1_docx_build_response.json",
        "svenska_2_grammatik_omprov_variant_1_med_facit",
    )
    accepted_first_anchors = {anchors[0] for _, anchors in state.accepted}
    assert {"body:0008", "body:0045"}.isdisjoint(accepted_first_anchors)
    pending = {chunk.anchor for chunk in state.pending}
    assert {"body:0008", "body:0045"} <= pending
    for anchor in ("body:0008", "body:0045"):
        (event,) = [e for e in state.events if e.code == "source_rule" and e.anchors[0] == anchor]
        assert "splits the text into units" in event.detail
        failure = next(f for f in state.failures if f.startswith(f"items[{event.item}] "))
        assert "source_rule" in failure and "splits the text into units" in failure
        assert anchor in state.reasons


def test_items_and_title_matching_source_structure_are_admitted():
    state = _admitted(
        "docx_build_v7/svenska_2_kursavslutande_prov_med_facit/round1.json",
        "svenska_2_kursavslutande_prov_med_facit",
    )
    assert not any("source_rule" in event.code for event in state.events)
    assert state.title is not None
    assert state.title.source_anchors == ("body:0002",)
    assert state.title.text == state.chunk_by_anchor["body:0002"].text


def _rejected_by_source_rule(state: DocxBuildState, phrase: str) -> list[str]:
    return [e.anchors[0] for e in state.events if e.code == "source_rule" and phrase in e.detail]


def test_items_keeping_their_printed_question_number_are_rejected_and_stay_pending():
    state = _admitted(
        "docx_build_v5/bf26_english_1_unit_test_kap_1_2_med_facit/round1.json",
        "bf26_english_1_unit_test_kap_1_2_med_facit",
    )
    kept = ["body:0059", "body:0063", "body:0067"]

    assert _rejected_by_source_rule(state, "question number that") == kept
    assert {anchors[0] for _, anchors in state.accepted}.isdisjoint(kept)
    assert set(kept) <= {chunk.anchor for chunk in state.pending}
    # The same section's other questions drop their numbers and stay admitted.
    assert {"body:0007", "body:0075"} <= {anchors[0] for _, anchors in state.accepted}


def test_items_printing_a_points_label_are_rejected_and_stay_pending():
    state = _admitted(
        "docx_build_v5/chapter_4_poetry_and_lyrics_quiz_med_facit/round1.json",
        "chapter_4_poetry_and_lyrics_quiz_med_facit",
    )
    labelled = _rejected_by_source_rule(state, "points label that")

    assert len(labelled) == 20
    assert labelled[0] == "body:0032" and labelled[-1] == "body:0147"
    assert {anchors[0] for _, anchors in state.accepted}.isdisjoint(labelled)
    assert set(labelled) <= {chunk.anchor for chunk in state.pending}


def test_items_dropping_their_label_are_admitted_in_every_current_recording():
    for exam_dir in sorted((_FIXTURES / "docx_build_v7").iterdir()):
        state = _admitted(f"docx_build_v7/{exam_dir.name}/round1.json", exam_dir.name)
        assert [e for e in state.events if e.code == "source_rule"] == [], exam_dir.name
        assert not state.failures or all("without item" in f for f in state.failures)


def test_sentence_wording_about_points_is_no_points_label():
    state = _admitted(
        "docx_build_v7/bf26_english_1_unit_test_kap_1_2_med_facit/round1.json",
        "bf26_english_1_unit_test_kap_1_2_med_facit",
    )
    items = {anchors[0]: item for item, anchors in state.accepted}

    for anchor in ("body:0059", "body:0063", "body:0067"):
        assert "Each correct match is worth 1 point." in " ".join(items[anchor].plain_text_lines())
