"""Answer-key wording is stripped from real corpus opening headings."""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    title_without_answer_key,
)
from tests.unit.domain.curated_apps.exam_workspace.source_rules_test_support import (
    chunks_by_anchor,
)
from tests.unit.scripts.exam_conversion_corpus_support import gold_exam, replayed

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


def opening_heading(chunks: tuple[DocxChunk, ...]) -> DocxChunk | None:
    return chunks[0] if chunks and chunks[0].kind == "heading" else None


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
def test_recorded_rounds_save_title_without_answer_key_label(stem: str, expected: str):
    document, _ = replayed(stem)
    assert document.title == expected
    assert document.title == gold_exam(stem).title
