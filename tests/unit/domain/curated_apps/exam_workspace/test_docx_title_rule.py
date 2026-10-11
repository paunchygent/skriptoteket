"""The title rule judged against real corpus opening headings."""

import json
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedMetadata
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    opening_heading,
    title_rule_violation,
    title_without_answer_key,
)
from tests.unit.domain.curated_apps.exam_workspace.source_rules_test_support import (
    chunks_by_anchor,
)
from tests.unit.scripts.exam_conversion_corpus_support import RECORDINGS, gold_exam, replayed

LABEL_BEARING_HEADINGS = (
    ("bf26_diagnostic_grammar_test_ht26_med_facit", "Diagnostic Grammar Test — BF26, HT26"),
    ("bf26_english_1_unit_test_kap_1_2_med_facit", "BF26 English 1 Unit Test — 45 minutes"),
    (
        "chapter_4_poetry_and_lyrics_quiz_med_facit",
        "Chapter 4: Poetry and Lyrics — Vocabulary and Terminology Quiz",
    ),
    ("metodprov_vetenskaplig_metod_med_facit", "Vetenskaplig metod - metodprov"),
    ("sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit", "Test Unit 3 Discuss and Argue"),
)
UNLABELED_HEADINGS = (
    "svenska_2_grammatik_omprov_variant_1_med_facit",
    "svenska_2_grammatik_omprov_variant_2_med_facit",
    "svenska_2_kursavslutande_prov_med_facit",
)


def _title(text: str, *anchors: str) -> ProducedMetadata:
    return ProducedMetadata.model_validate({"text": text, "source_anchors": list(anchors)})


def _title_violation(chunks: dict[str, DocxChunk], title: ProducedMetadata) -> str | None:
    heading = opening_heading(tuple(chunks.values()))
    return title_rule_violation(title, [chunks[a] for a in title.source_anchors], heading)


def test_title_copying_opening_heading_verbatim_passes():
    chunks = chunks_by_anchor("sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit")
    assert _title_violation(chunks, _title(chunks["body:0002"].text, "body:0002")) is None


def test_title_with_words_beyond_its_source_violates():
    chunks = chunks_by_anchor("sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit")
    title = _title(f"{chunks['body:0002'].text} extra", "body:0002")
    assert _title_violation(chunks, title) is not None


def test_title_anchored_away_from_opening_heading_names_the_heading():
    chunks = chunks_by_anchor("sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit")
    violation = _title_violation(chunks, _title(chunks["body:0003"].text, "body:0003"))
    assert violation is not None
    assert "body:0002" in violation


def test_title_joining_opening_heading_and_next_chunk_with_separator_passes():
    chunks = chunks_by_anchor("svenska_2_grammatik_omprov_variant_1_med_facit")
    text = f"{chunks['body:0002'].text} — {chunks['body:0003'].text}"
    assert _title_violation(chunks, _title(text, "body:0002", "body:0003")) is None


@pytest.mark.parametrize("stem, expected", LABEL_BEARING_HEADINGS)
def test_real_opening_heading_loses_only_answer_key_label_and_separator(stem: str, expected: str):
    heading = opening_heading(tuple(chunks_by_anchor(stem).values()))
    assert heading is not None
    assert title_without_answer_key(heading.text) == expected


@pytest.mark.parametrize("stem", UNLABELED_HEADINGS)
def test_real_opening_heading_without_answer_key_label_is_unchanged(stem: str):
    heading = opening_heading(tuple(chunks_by_anchor(stem).values()))
    assert heading is not None
    assert title_without_answer_key(heading.text) == heading.text


@pytest.mark.parametrize("stem, expected", LABEL_BEARING_HEADINGS)
def test_already_stripped_recorded_title_still_fails_verbatim_rule_and_admission(
    stem: str, expected: str
):
    chunks = chunks_by_anchor(stem)
    recorded = json.loads((RECORDINGS / stem / "round1.json").read_text())
    original = ProducedMetadata.model_validate(recorded["title"])
    heading = opening_heading(tuple(chunks.values()))
    assert heading is not None
    assert original.text == heading.text
    assert _title_violation(chunks, original) is None

    stripped = original.model_copy(update={"text": expected})
    assert _title_violation(chunks, stripped) is not None
    recorded["title"] = stripped.model_dump(mode="json")
    state = DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename=f"{stem}.docx",
        source_sha256=gold_exam(stem).source_sha256,
        chunks=tuple(chunks.values()),
    )
    admit_batch(recorded, state)
    assert state.title is None
    assert any(event.code == "title_source_rule" for event in state.events)


@pytest.mark.parametrize("stem, expected", LABEL_BEARING_HEADINGS)
def test_recorded_rounds_save_title_without_answer_key_label(stem: str, expected: str):
    document, _ = replayed(stem)
    assert document.title == expected
    assert document.title == gold_exam(stem).title
