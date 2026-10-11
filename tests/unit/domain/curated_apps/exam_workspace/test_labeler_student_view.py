"""Adversarial student-view cases from the real DOCX corpus (D14)."""

from __future__ import annotations

from functools import cache
from pathlib import Path

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.labeler_student_view import (
    ANSWER_SLOT,
    StudentLine,
    student_view,
    tight_heading,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)

pytestmark = pytest.mark.unit

CORPUS = Path("tests/fixtures/exam_conversion/docx_corpus")
DIAGNOSTIC = "bf26_diagnostic_grammar_test_ht26_med_facit"
GRAMMAR_VARIANT = "svenska_2_grammatik_omprov_variant_1_med_facit"
GRAMMAR_VARIANT_2 = "svenska_2_grammatik_omprov_variant_2_med_facit"


@cache
def _chunks(stem: str) -> tuple[DocxChunk, ...]:
    return PythonDocxExamChunker().chunk(content=(CORPUS / f"{stem}.docx").read_bytes())


def _by_anchor(stem: str, *anchors: str) -> list[DocxChunk]:
    chunks = {chunk.anchor: chunk for chunk in _chunks(stem)}
    return [chunks[anchor] for anchor in anchors]


@pytest.mark.parametrize("designated_key", [False, True])
def test_pure_key_label_and_inline_answer_never_become_a_student_slot(
    designated_key: bool,
) -> None:
    question = _by_anchor(DIAGNOSTIC, "body:0005", "body:0006")

    view = student_view(question, question[1:] if designated_key else [])

    assert view.lines == (
        StudentLine(
            anchor="body:0005",
            text="1. The most famous bands ____________ (spelar) at the festival every summer.",
        ),
    )
    assert view.question == view.lines[0].text
    assert view.answer_key == "Correct answer: play"


@pytest.mark.parametrize("anchor", ["body:0012", "body:0044"])
def test_accepted_alternatives_stay_in_key_without_leaking_into_student_text(anchor: str) -> None:
    key = _by_anchor(DIAGNOSTIC, anchor)

    view = student_view(key, key)

    assert view.lines == ()
    assert view.question == ""
    assert view.answer_key == key[0].text
    assert view.answer_key is not None
    assert "(Also accepted:" in view.answer_key


@pytest.mark.parametrize("key_only", [False, True])
def test_visible_subpart_response_designated_key_is_restored(key_only: bool) -> None:
    # Variant 2 q1's response lines were designated only as keys by the real grouping.
    keys = _by_anchor(GRAMMAR_VARIANT_2, "body:0010", "body:0011", "body:0012")

    view = student_view([] if key_only else keys, keys)

    assert view.lines == (
        StudentLine("body:0010", f"a) solrosornas {ANSWER_SLOT}"),
        StudentLine("body:0011", f"b) läsbarheten {ANSWER_SLOT}"),
        StudentLine("body:0012", f"c) handbollsspelarnas {ANSWER_SLOT}"),
    )
    assert view.answer_key == (
        "a) solrosornas Svar: sol (R) + ros (R) + or (B) + na (B) + s (B)\n"
        "b) läsbarheten Svar: läs (R) + bar (A) + het (A) + en (B)\n"
        "c) handbollsspelarnas Svar: hand (R) + boll (R) + foge-s + spel (R) "
        "+ are (A) + na (B) + s (B)"
    )
    assert "Svar:" not in view.question


def test_labelled_fields_preserve_key_shape_without_slot_number_prefixes() -> None:
    question = _by_anchor(GRAMMAR_VARIANT, "body:0025", "body:0026", "body:0027")

    view = student_view(question, [])

    assert view.lines[0] == StudentLine(question[0].anchor, question[0].marked_text)
    assert view.lines[1].text == f"a) de tre nya eleverna från Göteborg Huvudord: {ANSWER_SLOT}"
    assert view.answer_key == (
        "a) de tre nya eleverna från Göteborg Huvudord: eleverna\n"
        "b) min äldre systers trasiga mobiltelefon på köksbordet Huvudord: mobiltelefon"
    )
    assert "<i>" not in view.question
    assert "Slot " not in view.answer_key


def test_multiple_inline_fields_keep_one_complete_key_line() -> None:
    question = _by_anchor(GRAMMAR_VARIANT_2, "body:0057")

    view = student_view(question, question)

    assert view.question == (
        f"a) Jag hörde att brandlarmet ringde klockan två. Bisats: {ANSWER_SLOT} "
        f"Typ: {ANSWER_SLOT} Satsdel: {ANSWER_SLOT}"
    )
    assert view.answer_key == (
        "a) Jag hörde att brandlarmet ringde klockan två. "
        "Bisats: att brandlarmet ringde klockan två Typ: att-sats Satsdel: DO"
    )


def test_source_sequence_overrides_key_list_order_and_duplicate_anchors() -> None:
    question = _by_anchor(DIAGNOSTIC, "body:0005", "body:0006", "body:0007", "body:0008")
    # The driver gives all own chunks in source order, while key anchors may be unordered.
    view = student_view([*question, question[0], question[1]], [question[3], question[1]])

    assert [line.anchor for line in view.lines] == ["body:0005", "body:0007"]
    assert view.answer_key == "Correct answer: play\nCorrect answer: for"


def test_printed_question_points_and_standalone_instruction_totals_are_removed() -> None:
    question = _by_anchor(DIAGNOSTIC, "body:0003", "body:0004", "body:0005")

    view = student_view(question, [])

    assert [line.anchor for line in view.lines] == ["body:0004", "body:0005"]
    assert view.lines[0].text == "Translate the words in brackets into English."
    assert view.lines[1].text.endswith("at the festival every summer.")
    assert "(spelar)" in view.question
    assert "point" not in view.question
    assert view.answer_key is None
    assert student_view(_by_anchor(GRAMMAR_VARIANT_2, "body:0013"), []).lines == ()


def test_points_are_removed_from_section_instruction_without_removing_other_text() -> None:
    view = student_view(_by_anchor(GRAMMAR_VARIANT_2, "body:0006", "body:0009"), [])

    assert view.lines[0].text == "Del 1: Morfem och fraser,"
    assert view.lines[1].text.endswith("men ger inte egen poäng.")


def test_tight_heading_excludes_owned_question_heading_and_neighbouring_text() -> None:
    chunks = _chunks(GRAMMAR_VARIANT_2)
    excluded = frozenset({"body:0002", "body:0008", "body:0010", "body:0011", "body:0012"})

    heading = tight_heading(chunks, ["body:0009", "body:0010"], excluded)

    assert heading == "Del 1: Morfem och fraser,"
    assert "Använd" not in heading
    assert "poäng" not in heading
    assert tight_heading(chunks, ["body:0009"], excluded | {"body:0006"}) is None


def test_tight_heading_excludes_title_and_key_owned_headings() -> None:
    chunks = _chunks(GRAMMAR_VARIANT_2)

    assert tight_heading(chunks, ["body:0004"], frozenset({"body:0002"})) is None
    assert (
        tight_heading(
            chunks,
            ["body:0009"],
            frozenset({"body:0002", "body:0006", "body:0008"}),
        )
        is None
    )


def test_question_opening_document_has_no_preceding_heading() -> None:
    chunks = _chunks(GRAMMAR_VARIANT_2)

    assert tight_heading(chunks, [chunks[0].anchor], frozenset()) is None
