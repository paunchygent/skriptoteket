"""Source-bound completeness of the confirmed DOCX gold files and the authored grid exam."""

import hashlib
from collections import Counter
from pathlib import Path

import pytest
from docx import Document

from scripts.exam_conversion_eval.compare import compare_exam
from scripts.exam_conversion_eval.compare_questions import gold_questions
from scripts.exam_conversion_eval.gold import GoldExam

CORPUS = Path(__file__).resolve().parents[2] / "fixtures/exam_conversion/docx_corpus"
GOLD = CORPUS / "gold"
AUTHORED = "svenska_2_kategorisera_ordklasser_med_facit"

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
    assert drafts == sources == set(SOURCE_COUNTS) | {AUTHORED}


@pytest.mark.parametrize("stem", SOURCE_COUNTS)
def test_gold_schema_source_hash_and_complete_item_counts(stem: str) -> None:
    source = CORPUS / f"{stem}.docx"
    gold = GoldExam.model_validate_json((GOLD / f"{stem}.json").read_bytes())
    assert gold.source_filename == source.name
    assert gold.source_sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert gold.source_sha256 == source.with_suffix(".docx.sha256").read_text().split()[0]
    count, points = SOURCE_COUNTS[stem]
    assert len(gold.questions) == count
    assert sum(item.points or 0 for item in gold.questions) == points
    assert len({item.source_label for item in gold.questions}) == count
    assert gold.confirmed is True
    assert gold.confirmation_note is not None and "2026-10-10" in gold.confirmation_note


def test_source_matching_tables_and_word_banks_are_preserved() -> None:
    english = GoldExam.model_validate_json(
        (GOLD / "bf26_english_1_unit_test_kap_1_2_med_facit.json").read_bytes()
    )
    matches = [item for item in english.questions if item.kind == "matching"]
    assert len(matches) == 3
    assert all(item.points == 3 and len(item.pairs) == 3 for item in matches)
    poetry = GoldExam.model_validate_json(
        (GOLD / "chapter_4_poetry_and_lyrics_quiz_med_facit.json").read_bytes()
    )
    word_bank_items = [item for item in poetry.questions if item.kind == "gap_fill"]
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
    assert len(diagnostic.questions[6].gaps) == 2
    assert diagnostic.questions[6].points == 2
    vocabulary = GoldExam.model_validate_json(
        (GOLD / "sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit.json").read_bytes()
    )
    assert len(vocabulary.questions[41].gaps) == 2
    assert vocabulary.questions[41].points == 2


@pytest.mark.parametrize("stem", SOURCE_COUNTS)
def test_gold_compares_equal_to_itself_without_unresolved_questions(stem: str) -> None:
    gold = GoldExam.model_validate_json((GOLD / f"{stem}.json").read_bytes())
    comparison = compare_exam(gold, gold.items)
    assert [item.mismatches for item in comparison.items if not item.passed] == []
    assert comparison.passed
    assert not comparison.unconfirmed


def test_the_authored_category_sorting_exam_is_labelled_and_source_bound() -> None:
    source = CORPUS / f"{AUTHORED}.docx"
    gold = GoldExam.model_validate_json((GOLD / f"{AUTHORED}.json").read_bytes())
    assert gold.source_filename == source.name
    assert gold.source_sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert gold.source_sha256 == source.with_suffix(".docx.sha256").read_text().split()[0]
    assert gold.confirmed is False, "an agent-authored fixture carries no user confirmation"
    assert len(gold.questions) == 2
    assert sum(item.points or 0 for item in gold.questions) == 7
    assert all(item.kind == "matching" for item in gold.questions)
    keyed = Counter(pair.left for item in gold.questions for pair in item.pairs)
    assert max(keyed.values()) >= 2, "one grid row keys two correct categories"
    unused = [
        right
        for item in gold.questions
        for right in gold_questions((item,))[0].view.match_right
        if right not in {pair.right for pair in item.pairs}
    ]
    assert unused, "one grid carries a category no tick uses"
    tables = Document(str(source)).tables
    assert len(tables) >= 2, "the exam has at least two category-sorting tables"
    assert all(len(table.columns) >= 3 for table in tables)
    comparison = compare_exam(gold, gold.items)
    assert comparison.passed
    assert [item.mismatches for item in comparison.items if not item.passed] == []
    assert comparison.unconfirmed
    readme = (GOLD / "README.md").read_text()
    assert AUTHORED in readme
    assert "agent-authored" in readme.casefold()
