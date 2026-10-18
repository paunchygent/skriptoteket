"""Block-structure indentation tests for Exam.net QTI item serialization.

Purpose:
    Prove that ``serialize_qti_assessment_item`` indents block structure only and
    never inserts whitespace inside mixed inline content: nested marks, marked
    runs, a plain run between marks, and a paragraph that starts with a mark keep
    the exact text the item was built with, while structure-only sections keep
    the whitespace ``ElementTree.indent`` gives them.

Relationships:
    - Exercises `domain.examnet_qti_item_xml` with contract items built directly,
      like `test_examnet_qti_inline_prompt` in this directory.
"""

from __future__ import annotations

from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiPromptGap,
    ExamNetQtiPromptParagraph,
    ExamNetQtiPromptText,
    ExamNetQtiTextEntryGap,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_xml import QTI_NAMESPACE

pytestmark = pytest.mark.unit

_MARKED_RUNS = (
    ExamNetQtiPromptParagraph(
        segments=(
            ExamNetQtiPromptText("Bold", marks=("bold",)),
            ExamNetQtiPromptText(" och "),
            ExamNetQtiPromptText("kursiv", marks=("italic",)),
            ExamNetQtiPromptText(" tillsammans."),
        )
    ),
    ExamNetQtiPromptParagraph(segments=(ExamNetQtiPromptText("x", marks=("bold", "italic")),)),
    ExamNetQtiPromptParagraph(
        heading_level=2,
        segments=(ExamNetQtiPromptText("Rubrik", marks=("underline",)),),
    ),
)


def _tag(local_name: str) -> str:
    return f"{{{QTI_NAMESPACE}}}{local_name}"


def _free_text_item(
    paragraphs: tuple[ExamNetQtiPromptParagraph, ...],
) -> ExamNetQtiItem:
    return ExamNetQtiItem(
        item_id="q1",
        sequence=1,
        title="Fråga 1",
        interaction_type=ExamNetQtiInteractionType.FREE_TEXT,
        prompt_lines=("Beskriv bilden.",),
        max_score=1,
        prompt_paragraphs=paragraphs,
    )


def _gap_fill_item(
    paragraphs: tuple[ExamNetQtiPromptParagraph, ...],
) -> ExamNetQtiItem:
    return ExamNetQtiItem(
        item_id="q2",
        sequence=2,
        title="Lucktext",
        interaction_type=ExamNetQtiInteractionType.GAP_FILL,
        prompt_lines=("Fyll i [___] och [___].",),
        max_score=1,
        text_entry_gaps=(
            ExamNetQtiTextEntryGap(
                response_identifier="RESPONSE_gap_001",
                label="Lucka 1",
                accepted_values=("alfa",),
            ),
            ExamNetQtiTextEntryGap(
                response_identifier="RESPONSE_gap_002",
                label="Lucka 2",
                accepted_values=("beta",),
            ),
        ),
        prompt_paragraphs=paragraphs,
    )


def _paragraphs(root: ElementTree.Element) -> list[ElementTree.Element]:
    return [
        element
        for element in root.iter()
        if element.tag in (_tag("p"), _tag("h1"), _tag("h2"), _tag("h3"))
    ]


def test_nested_marks_keep_the_inner_text_and_add_no_whitespace() -> None:
    item = _free_text_item(
        (
            ExamNetQtiPromptParagraph(
                segments=(ExamNetQtiPromptText("x", marks=("bold", "italic")),)
            ),
        )
    )

    raw = serialize_qti_assessment_item(item)

    assert "<strong><em>x</em></strong>" in raw.decode("utf-8")
    root = ElementTree.fromstring(raw)
    strong = root.find(f".//{_tag('strong')}")
    assert strong is not None
    assert strong.text in (None, "")
    (em,) = list(strong)
    assert em.tag == _tag("em")
    assert em.text == "x"
    assert em.tail in (None, "")


def test_single_space_between_two_marked_runs_survives() -> None:
    item = _free_text_item(
        (
            ExamNetQtiPromptParagraph(
                segments=(
                    ExamNetQtiPromptText("a", marks=("bold",)),
                    ExamNetQtiPromptText(" "),
                    ExamNetQtiPromptText("b", marks=("italic",)),
                )
            ),
        )
    )

    raw = serialize_qti_assessment_item(item)

    assert "<strong>a</strong> <em>b</em>" in raw.decode("utf-8")
    root = ElementTree.fromstring(raw)
    strong = root.find(f".//{_tag('strong')}")
    assert strong is not None
    assert strong.tail == " "


def test_paragraph_starting_with_a_marked_run_gets_no_leading_whitespace() -> None:
    item = _gap_fill_item(
        (
            ExamNetQtiPromptParagraph(
                segments=(
                    ExamNetQtiPromptText("Inledning", marks=("bold",)),
                    ExamNetQtiPromptText(" "),
                    ExamNetQtiPromptGap(0),
                    ExamNetQtiPromptText(" fortsätter."),
                )
            ),
        )
    )

    raw = serialize_qti_assessment_item(item)

    assert "<p><strong>" in raw.decode("utf-8")


def test_block_elements_stay_indented() -> None:
    item = _free_text_item(_MARKED_RUNS)

    raw = serialize_qti_assessment_item(item).decode("utf-8")

    assert "\n  <qti-item-body>" in raw
    assert "\n    <qti-default-value>" in raw
    assert "\n      <qti-value>" in raw


def test_every_built_paragraph_round_trips_with_its_exact_run_text() -> None:
    item = _gap_fill_item(
        (
            ExamNetQtiPromptParagraph(
                segments=(
                    ExamNetQtiPromptText("Bold", marks=("bold",)),
                    ExamNetQtiPromptText(" och "),
                    ExamNetQtiPromptText("kursiv", marks=("italic",)),
                    ExamNetQtiPromptText(" tillsammans."),
                )
            ),
            ExamNetQtiPromptParagraph(
                segments=(
                    ExamNetQtiPromptText("Före "),
                    ExamNetQtiPromptGap(0),
                    ExamNetQtiPromptText(" med "),
                    ExamNetQtiPromptGap(1),
                    ExamNetQtiPromptText(" efter."),
                )
            ),
            ExamNetQtiPromptParagraph(
                segments=(ExamNetQtiPromptText("x", marks=("bold", "italic")),)
            ),
        )
    )

    root = ElementTree.fromstring(serialize_qti_assessment_item(item))

    paragraphs = _paragraphs(root)
    assert ["".join(paragraph.itertext()) for paragraph in paragraphs] == [
        "Bold och kursiv tillsammans.",
        "Före  med  efter.",
        "x",
    ]


def test_structure_only_sections_keep_the_element_tree_indent_whitespace() -> None:
    item = ExamNetQtiItem(
        item_id="q2",
        sequence=2,
        title="Fråga 2",
        interaction_type=ExamNetQtiInteractionType.SINGLE_CHOICE,
        prompt_lines=("Välj rätt alternativ.",),
        max_score=1,
        choices=(ExamNetQtiChoice(identifier="alfa", text="Alfa"),),
        correct_choice_identifiers=("alfa",),
    )

    raw = serialize_qti_assessment_item(item).decode("utf-8")

    assert (
        '  <qti-response-declaration identifier="RESPONSE" cardinality="single" '
        'base-type="identifier">\n'
        "    <qti-correct-response>\n"
        "      <qti-value>alfa</qti-value>\n"
        "    </qti-correct-response>"
    ) in raw
