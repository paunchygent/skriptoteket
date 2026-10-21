"""Filename fallback titles assembled from real DOCX corpus chunks."""

from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import assemble_build_result
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    title_without_answer_key,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from tests.unit.domain.curated_apps.exam_workspace.source_rules_test_support import (
    chunks_by_anchor,
)
from tests.unit.scripts.exam_conversion_corpus_support import gold_exam

CORPUS_TITLES = (
    "bf26_diagnostic_grammar_test_ht26",
    "bf26_english_1_unit_test_kap_1_2",
    "chapter_4_poetry_and_lyrics_quiz",
    "metodprov_vetenskaplig_metod",
    "sa24_solid_gold_3_unit_3_discuss_and_argue",
    "svenska_2_grammatik_omprov_variant_1",
    "svenska_2_grammatik_omprov_variant_2",
    "svenska_2_kursavslutande_prov",
)
SA24 = "sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit"


def _fallback(filename: str, corpus_stem: str = SA24) -> NativeExamDocument:
    chunks = tuple(chunks_by_anchor(corpus_stem).values())
    return assemble_build_result(
        origin_kind="docx_import",
        document_id=uuid4(),
        filename=filename,
        source_sha256=gold_exam(corpus_stem).source_sha256,
        chunks=chunks,
        review_reasons={chunk.anchor: "Ej konverterat källstycke." for chunk in chunks},
        title=None,
    ).document


@pytest.mark.parametrize("expected_stem", CORPUS_TITLES)
def test_real_corpus_filename_fallback_removes_whole_med_facit_label(expected_stem: str):
    corpus_stem = f"{expected_stem}_med_facit"
    filename = f"{corpus_stem}.docx"
    document = _fallback(filename, corpus_stem)
    assert document.title == f"{expected_stem}.docx"
    assert document.origin.source_filename == filename


@pytest.mark.parametrize(
    "phrase", ("answer key", "key", "facit", "med facit", "with answers", "svar")
)
@pytest.mark.parametrize("word_separator", ("_", "-"))
@pytest.mark.parametrize("edge", ("prefix", "suffix"))
def test_filename_labels_remove_whole_phrase_and_delimiter_preserving_remainder(
    phrase: str, word_separator: str, edge: str
):
    label = phrase.upper().replace(" ", word_separator)
    remainder = "Sa24__Discuss-and_Argue"
    stem = f"{label}__--{remainder}" if edge == "prefix" else f"{remainder}__--{label}"
    filename = f"{stem}.DoCx"
    document = _fallback(filename)
    assert document.title == f"{remainder}.DoCx"
    assert document.origin.source_filename == filename


@pytest.mark.parametrize("delimiter", (" — ", ": ", ", "))
@pytest.mark.parametrize("edge", ("prefix", "suffix"))
def test_filename_multiword_label_keeps_existing_punctuation_delimiters(delimiter: str, edge: str):
    remainder = "Sa24__Discuss-and_Argue"
    stem = (
        f"answer-key{delimiter}{remainder}"
        if edge == "prefix"
        else f"{remainder}{delimiter}med_facit"
    )
    filename = f"{stem}.docx"
    document = _fallback(filename)
    assert document.title == f"{remainder}.docx"
    assert document.origin.source_filename == filename


@pytest.mark.parametrize("edge", ("prefix", "suffix"))
def test_parenthesized_filename_label_consumes_whole_joining_delimiter(edge: str):
    remainder = "Sa24__Discuss-and_Argue"
    stem = f"(with-answers)__--{remainder}" if edge == "prefix" else f"{remainder}__--(med_facit)"
    filename = f"{stem}.docx"
    document = _fallback(filename)
    assert document.title == f"{remainder}.docx"
    assert document.origin.source_filename == filename


def test_in_word_key_filename_is_unchanged():
    filename = "Keynote__Discuss-and_Argue.docx"
    document = _fallback(filename)
    assert document.title == filename
    assert document.origin.source_filename == filename


@pytest.mark.parametrize(
    "heading", ("answer-key_Exam", "med-facit_Exam", "Exam_med_facit", "Exam_answer_key")
)
def test_filename_word_separators_remain_literal_in_heading_mode(heading: str):
    assert title_without_answer_key(heading) == heading
