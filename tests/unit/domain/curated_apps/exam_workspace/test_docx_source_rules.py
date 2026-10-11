"""Source-structure rules judged against real recorded model output and real corpus chunks."""

import json
from pathlib import Path

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedItem,
    ProducedMetadata,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    definition_context,
    item_rule_violation,
    opening_heading,
    title_rule_violation,
    with_defined_short_forms,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)

_FIXTURES = Path("tests/fixtures/exam_conversion")


def _chunks(docx: str) -> dict[str, DocxChunk]:
    chunks = PythonDocxExamChunker().chunk(
        content=(_FIXTURES / f"docx_corpus/{docx}.docx").read_bytes()
    )
    return {chunk.anchor: chunk for chunk in chunks}


def _items(recording: str) -> list[ProducedItem]:
    content = json.loads((_FIXTURES / recording).read_text())
    return [ProducedItem.model_validate(raw) for raw in content["items"]]


def _violations(recording: str, docx: str) -> dict[tuple[str, ...], str | None]:
    chunks = _chunks(docx)
    return {
        item.source_anchors: item_rule_violation(item, [chunks[a] for a in item.source_anchors])
        for item in _items(recording)
    }


def test_blank_marker_without_gap_or_options_violates_and_other_items_pass():
    violations = _violations(
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
    violations = _violations(recording, docx)
    flagged = {anchors[0]: v for anchors, v in violations.items() if v is not None}
    assert set(flagged) == {"body:0008", "body:0045"}
    assert all("free_text" in violation for violation in flagged.values())
    assert len(violations) - len(flagged) == 6


def test_gaps_beyond_blank_markers_violate_as_facit_created_gaps():
    violations = _violations(
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
    violations = _violations(recording, docx)
    assert violations
    assert {anchors: v for anchors, v in violations.items() if v is not None} == {}


def test_review_outcome_never_violates():
    chunks = _chunks("svenska_2_grammatik_omprov_variant_1_med_facit")
    item = next(
        item
        for item in _items("svenska_2_grammatik_variant_1_docx_build_response.json")
        if item.source_anchors[0] == "body:0008"
    )
    sources = [chunks[a] for a in item.source_anchors]
    assert item_rule_violation(item, sources) is not None
    review = item.model_copy(update={"outcome": "review", "review_reason": "x"})
    assert item_rule_violation(review, sources) is None


def _title(text: str, *anchors: str) -> ProducedMetadata:
    return ProducedMetadata.model_validate({"text": text, "source_anchors": list(anchors)})


def _title_violation(chunks: dict[str, DocxChunk], title: ProducedMetadata) -> str | None:
    heading = opening_heading(tuple(chunks.values()))
    return title_rule_violation(title, [chunks[a] for a in title.source_anchors], heading)


def test_title_copying_opening_heading_verbatim_passes():
    chunks = _chunks("sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit")
    assert _title_violation(chunks, _title(chunks["body:0002"].text, "body:0002")) is None


def test_title_with_words_beyond_its_source_violates():
    chunks = _chunks("sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit")
    title = _title(f"{chunks['body:0002'].text} extra", "body:0002")
    assert _title_violation(chunks, title) is not None


def test_title_anchored_away_from_opening_heading_names_the_heading():
    chunks = _chunks("sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit")
    violation = _title_violation(chunks, _title(chunks["body:0003"].text, "body:0003"))
    assert violation is not None
    assert "body:0002" in violation


def test_title_joining_opening_heading_and_next_chunk_with_separator_passes():
    chunks = _chunks("svenska_2_grammatik_omprov_variant_1_med_facit")
    text = f"{chunks['body:0002'].text} — {chunks['body:0003'].text}"
    assert _title_violation(chunks, _title(text, "body:0002", "body:0003")) is None


def _gap_values(recording: str, docx: str) -> dict[str, list[list[str]]]:
    chunks = PythonDocxExamChunker().chunk(
        content=(_FIXTURES / f"docx_corpus/{docx}.docx").read_bytes()
    )
    result = {}
    for item in _items(recording):
        widened = with_defined_short_forms(item, definition_context(chunks, item.source_anchors))
        result[item.source_anchors[0]] = [
            list(s.accepted_values) for p in widened.body for s in p.segments if s.kind == "gap"
        ]
    return result


def test_facit_term_defined_in_the_section_instruction_also_accepts_its_short_form():
    values = _gap_values(
        "svenska_2_grammatik_variant_2_docx_build_response.json",
        "svenska_2_grammatik_omprov_variant_2_med_facit",
    )
    assert values["body:0037"] == [
        ["adverbial", "Adv"],
        ["indirekt objekt", "IO"],
        ["predikativ/predikatsfyllnad", "Pf"],
        ["direkt objekt", "DO"],
    ]
    # Short forms listed without "=" define nothing.
    assert values["body:0016"] == [["NF"], ["VF"], ["PF"], ["PF"]]


def test_facit_already_in_short_form_gains_no_term():
    recording = "svenska_2_kursavslutande_prov_docx_build_response.json"
    chunks = _chunks("svenska_2_kursavslutande_prov_med_facit")
    original = {
        item.source_anchors[0]: [
            list(s.accepted_values) for p in item.body for s in p.segments if s.kind == "gap"
        ]
        for item in _items(recording)
    }
    # The questions' own instructions define their labels with "=".
    assert sum(chunks[a].text.count("=") for a in chunks) >= 6
    assert _gap_values(recording, "svenska_2_kursavslutande_prov_med_facit") == original


def test_term_added_beside_a_short_form_facit_is_dropped():
    """A live round added each defined term next to the short form the inline facit writes."""
    chunks = PythonDocxExamChunker().chunk(
        content=(
            _FIXTURES / "docx_corpus/svenska_2_kursavslutande_prov_med_facit.docx"
        ).read_bytes()
    )
    by_anchor = {chunk.anchor: chunk for chunk in chunks}
    item = next(
        item
        for item in _items("svenska_2_kursavslutande_prov_docx_build_response.json")
        if item.source_anchors[0] == "body:0061"
    )
    terms = iter(("rotmorfem", "avledningsmorfem", "böjningsmorfem"))
    padded = item.model_copy(
        update={
            "body": tuple(
                p.model_copy(
                    update={
                        "segments": tuple(
                            s.model_copy(
                                update={"accepted_values": (*s.accepted_values, next(terms))}
                            )
                            if s.kind == "gap"
                            else s
                            for s in p.segments
                        )
                    }
                )
                for p in item.body
            )
        }
    )
    assert "R = rotmorfem" in by_anchor["body:0062"].text

    widened = with_defined_short_forms(padded, definition_context(chunks, item.source_anchors))

    assert widened == item
