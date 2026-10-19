"""Exam.net QTI formatting for entry labels and plain shared values.

Purpose:
    Prove that choice labels and matching entries carry the native marks and
    headings as semantic XML elements, while the DigiExam lane's plain shared
    values keep the positionless rendering.

Relationships:
    - Exercises `domain.examnet_qti_export` and the shared item serialization
      with native documents built directly.
    - Companions `test_examnet_qti_formatting_export.py`, which owns prompt,
      instruction and unformatted-structure coverage.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiEvaluationMode,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiMatchEntry,
    ExamNetQtiPromptParagraph,
    ExamNetQtiPromptText,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_matching import (
    NativeMatchLeft,
    NativeMatchPair,
    NativeMatchRight,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from tests.unit.domain.curated_apps.exam_workspace.examnet_qti_export_test_support import (
    document,
    paragraph,
    review_complete,
    serialize,
    tag,
    text,
)

pytestmark = pytest.mark.unit


class TestChoiceAndMatchFormatting:
    def test_choice_labels_render_marks_and_headings_and_keep_a_plain_label(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.SINGLE_CHOICE,
            body=(paragraph(text("Välj.")),),
            points=1,
            choices=(
                NativeChoice(
                    choice_id="choice_001",
                    body=(paragraph(text("fet", "bold"), text(" två", "italic"), heading_level=2),),
                ),
                NativeChoice(choice_id="choice_002", body=(paragraph(text("vanlig")),)),
            ),
            answer_key=NativeAnswerKey(
                origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
                correct_choice_ids=("choice_001",),
            ),
            review=review_complete(),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(document(item))

        assert [choice.text for choice in qti_item.choices] == ["fet två", "vanlig"]
        _, root = serialize(qti_item)

        choices = root.findall(f".//{tag('qti-simple-choice')}")
        assert len(choices) == 2
        rich, plain = choices
        rich_heading = rich.find(tag("h2"))
        strong = rich.find(f".//{tag('strong')}")
        emphasis = rich.find(f".//{tag('em')}")
        plain_paragraph = plain.find(tag("p"))
        assert rich_heading is not None
        assert strong is not None and strong.text == "fet"
        assert emphasis is not None and emphasis.text == " två"
        assert plain_paragraph is not None and plain_paragraph.text == "vanlig"

    def test_matching_entries_render_marks_and_keep_a_plain_label(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.MATCHING,
            body=(paragraph(text("Matcha.")),),
            points=1,
            tick_points=Decimal("1"),
            match_left=(
                NativeMatchLeft(
                    left_id="left_001",
                    body=(paragraph(text("A", "bold")),),
                ),
            ),
            match_right=(
                NativeMatchRight(
                    right_id="right_001",
                    body=(paragraph(text("ett", "italic")),),
                ),
                NativeMatchRight(right_id="right_002", body=(paragraph(text("två")),)),
            ),
            answer_key=NativeAnswerKey(
                origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
                match_pairs=(NativeMatchPair(left_id="left_001", right_id="right_001"),),
            ),
            review=review_complete(),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(document(item))

        assert [entry.text for entry in qti_item.match_left] == ["A"]
        assert [entry.text for entry in qti_item.match_right] == ["ett", "två"]
        _, root = serialize(qti_item)

        entries = root.findall(f".//{tag('qti-simple-associable-choice')}")
        assert len(entries) == 3
        left, right = entries[0], entries[1]
        strong = left.find(f".//{tag('strong')}")
        emphasis = right.find(f".//{tag('em')}")
        plain_paragraph = entries[2].find(tag("p"))
        assert strong is not None and strong.text == "A"
        assert emphasis is not None and emphasis.text == "ett"
        assert plain_paragraph is not None and plain_paragraph.text == "två"


class TestPlainSharedValues:
    def test_shared_defaults_stay_empty_for_the_digiexam_lane(self) -> None:
        assert ExamNetQtiPromptText("x").marks == ()
        paragraph_ = ExamNetQtiPromptParagraph(segments=(ExamNetQtiPromptText("x"),))
        assert paragraph_.heading_level is None
        assert ExamNetQtiChoice("choice_001", "Ett").body == ()
        assert ExamNetQtiMatchEntry("left_001", "A").body == ()

    def test_a_plain_shared_choice_renders_positionless_text(self) -> None:
        item = ExamNetQtiItem(
            item_id="q1",
            sequence=1,
            title="Fråga 1",
            interaction_type=ExamNetQtiInteractionType.SINGLE_CHOICE,
            prompt_lines=("Välj ett.",),
            max_score=1,
            evaluation_mode=ExamNetQtiEvaluationMode.AUTOMATIC,
            choices=(ExamNetQtiChoice("choice_001", "Ett"), ExamNetQtiChoice("choice_002", "Två")),
            correct_choice_identifiers=("choice_001",),
        )

        _, root = serialize(item)

        choices = root.findall(f".//{tag('qti-simple-choice')}")
        assert [choice.text for choice in choices] == ["Ett", "Två"]
        assert [list(choice) for choice in choices] == [[], []]
