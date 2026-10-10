"""Source-bound completeness of the eight user-confirmed DOCX gold files."""

import hashlib
from pathlib import Path

import pytest

from scripts.exam_conversion_eval.compare import compare_exam
from scripts.exam_conversion_eval.gold import GoldExam

CORPUS = Path(__file__).resolve().parents[2] / "fixtures/exam_conversion/docx_corpus"
GOLD = CORPUS / "gold"

# Counts are hand-read source question boundaries, independent of converter output.
SOURCE_COUNTS = {
    "bf26_diagnostic_grammar_test_ht26_med_facit": (104, 105),
    "bf26_english_1_unit_test_kap_1_2_med_facit": (53, 59),
    "chapter_4_poetry_and_lyrics_quiz_med_facit": (28, 28),
    "metodprov_vetenskaplig_metod_med_facit": (16, 20),
    "sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit": (73, 74),
    "svenska_2_grammatik_omprov_variant_1_med_facit": (8, 38),
    "svenska_2_grammatik_omprov_variant_2_med_facit": (8, 38),
    "svenska_2_kursavslutande_prov_med_facit": (24, 36),
}


def test_one_gold_file_per_source_exam() -> None:
    sources = {path.stem for path in CORPUS.glob("*.docx")}
    drafts = {path.stem for path in GOLD.glob("*.json")}
    assert len(sources) == 8
    assert drafts == sources == set(SOURCE_COUNTS)


@pytest.mark.parametrize("stem", SOURCE_COUNTS)
def test_gold_schema_source_hash_and_complete_item_counts(stem: str) -> None:
    source = CORPUS / f"{stem}.docx"
    gold = GoldExam.model_validate_json((GOLD / f"{stem}.json").read_bytes())
    assert gold.source_filename == source.name
    assert gold.source_sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert gold.source_sha256 == source.with_suffix(".docx.sha256").read_text().split()[0]
    count, points = SOURCE_COUNTS[stem]
    assert len(gold.items) == count
    assert sum(item.points or 0 for item in gold.items) == points
    assert len({item.source_label for item in gold.items}) == count
    assert gold.confirmed is True
    assert gold.confirmation_note is not None and "2026-10-10" in gold.confirmation_note


def test_source_matching_tables_and_word_banks_are_preserved() -> None:
    english = GoldExam.model_validate_json(
        (GOLD / "bf26_english_1_unit_test_kap_1_2_med_facit.json").read_bytes()
    )
    matches = [item for item in english.items if item.kind == "matching"]
    assert len(matches) == 3
    assert all(item.points == 3 and len(item.pairs) == 3 for item in matches)
    poetry = GoldExam.model_validate_json(
        (GOLD / "chapter_4_poetry_and_lyrics_quiz_med_facit.json").read_bytes()
    )
    word_bank_items = [item for item in poetry.items if item.kind == "gap_fill"]
    assert len(word_bank_items) == 7
    assert all("alliteration | cherish | diction" in item.prompt for item in word_bank_items)
    assert [item.gaps[0].accepted_values[0] for item in word_bank_items] == [
        "cherish",
        "traverse",
        "humiliate",
        "out of the blue",
        "line",
        "diction",
        "alliteration",
    ]


def test_multigap_source_questions_remain_single_items() -> None:
    diagnostic = GoldExam.model_validate_json(
        (GOLD / "bf26_diagnostic_grammar_test_ht26_med_facit.json").read_bytes()
    )
    assert len(diagnostic.items[6].gaps) == 2
    assert diagnostic.items[6].points == 2
    vocabulary = GoldExam.model_validate_json(
        (GOLD / "sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit.json").read_bytes()
    )
    assert len(vocabulary.items[41].gaps) == 2
    assert vocabulary.items[41].points == 2


@pytest.mark.parametrize("stem", SOURCE_COUNTS)
def test_gold_compares_equal_to_itself_without_unresolved_questions(stem: str) -> None:
    gold = GoldExam.model_validate_json((GOLD / f"{stem}.json").read_bytes())
    comparison = compare_exam(gold, gold.items)
    assert [item.mismatches for item in comparison.items if not item.passed] == []
    assert comparison.passed
    assert not comparison.unconfirmed
