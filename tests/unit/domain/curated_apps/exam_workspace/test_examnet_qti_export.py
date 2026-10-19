"""Mapping tests for free-text and choice items in the native exam -> Exam.net QTI adapter."""

from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiEvaluationMode,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import QTI_NAMESPACE
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_criteria import (
    NativeExamCriterion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
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
    document_of,
    review_complete,
    text_body,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import plain_body


class TestFreeTextMapping:
    def test_free_text_with_points_uses_criterion_points(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.FREE_TEXT,
            writing_lines=8,
            body=text_body("Resonera om satsdelar."),
            points=4,
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
            review=review_complete(),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(document_of((item,)))

        assert qti_item.interaction_type is ExamNetQtiInteractionType.FREE_TEXT
        assert qti_item.item_id == "item_001"
        assert qti_item.title == "Fråga 1"
        assert qti_item.prompt_lines == ("Resonera om satsdelar.",)
        assert qti_item.max_score == 4
        assert qti_item.free_text_criterion_points == 4
        assert qti_item.evaluation_mode is ExamNetQtiEvaluationMode.AUTOMATIC
        assert qti_item.source_item_type == "free_text"

    def test_free_text_without_points_degrades_to_manual_unkeyed(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.FREE_TEXT,
            writing_lines=8,
            body=text_body("Resonera fritt."),
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
            review=review_complete(),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(document_of((item,)))

        assert qti_item.evaluation_mode is ExamNetQtiEvaluationMode.MANUAL_UNKEYED
        assert qti_item.free_text_criterion_points is None
        assert qti_item.title == "Fråga 1"

    def test_free_text_criteria_flatten_to_one_point_rows(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.FREE_TEXT,
            writing_lines=8,
            body=text_body("Resonera om satsdelar."),
            points=3,
            criteria=(
                NativeExamCriterion(text="Ett korrekt exempel.", points=2),
                NativeExamCriterion(text="En korrekt förklaring.", points=1),
            ),
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
            review=review_complete(),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(document_of((item,)))

        assert qti_item.interaction_type is ExamNetQtiInteractionType.FREE_TEXT
        assert qti_item.evaluation_mode is ExamNetQtiEvaluationMode.AUTOMATIC
        assert qti_item.max_score == 3
        assert qti_item.free_text_criterion_points == 1
        root = ElementTree.fromstring(serialize_qti_assessment_item(qti_item))
        mapping = root.find(f".//{{{QTI_NAMESPACE}}}qti-mapping")
        assert mapping is not None
        assert mapping.attrib == {
            "default-value": "0",
            "lower-bound": "0",
            "upper-bound": "3",
        }
        assert [
            (entry.attrib["map-key"], entry.attrib["mapped-value"])
            for entry in mapping.findall(f"{{{QTI_NAMESPACE}}}qti-map-entry")
        ] == [("CRITERION_1", "1"), ("CRITERION_2", "1"), ("CRITERION_3", "1")]
        package_xml = serialize_qti_assessment_item(qti_item).decode("utf-8")
        assert "Ett korrekt exempel." not in package_xml
        assert "En korrekt förklaring." not in package_xml

    def test_an_inconsistent_criterion_ratio_is_a_programming_error(self) -> None:
        qti_item = ExamNetQtiItem(
            item_id="item_001",
            sequence=1,
            title="Fråga 1",
            interaction_type=ExamNetQtiInteractionType.FREE_TEXT,
            prompt_lines=("Resonera.",),
            max_score=4,
            free_text_criterion_points=3,
        )

        with pytest.raises(ValueError, match="positive whole number"):
            serialize_qti_assessment_item(qti_item)


class TestChoiceMapping:
    def test_single_choice_maps_choices_and_correct_identifier(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.SINGLE_CHOICE,
            body=text_body("Välj rätt alternativ."),
            points=2,
            choices=(
                NativeChoice(choice_id="choice_001", body=plain_body("  Alternativ   ett ")),
                NativeChoice(choice_id="choice_002", body=plain_body("Alternativ två")),
            ),
            answer_key=NativeAnswerKey(
                origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
                correct_choice_ids=("choice_002",),
            ),
            review=review_complete(),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(document_of((item,)))

        assert qti_item.interaction_type is ExamNetQtiInteractionType.SINGLE_CHOICE
        assert tuple(choice.identifier for choice in qti_item.choices) == (
            "choice_001",
            "choice_002",
        )
        assert qti_item.choices[0].text == "Alternativ ett"
        assert qti_item.correct_choice_identifiers == ("choice_002",)
        assert qti_item.evaluation_mode is ExamNetQtiEvaluationMode.AUTOMATIC
        assert qti_item.max_score == 2

    def test_multiple_response_keeps_every_correct_identifier(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.MULTIPLE_RESPONSE,
            body=text_body("Markera alla rätta alternativ."),
            points=3,
            choices=(
                NativeChoice(choice_id="choice_001", body=plain_body("Ett")),
                NativeChoice(choice_id="choice_002", body=plain_body("Två")),
                NativeChoice(choice_id="choice_003", body=plain_body("Tre")),
            ),
            answer_key=NativeAnswerKey(
                origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED,
                correct_choice_ids=("choice_001", "choice_003"),
            ),
            review=review_complete(),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(document_of((item,)))

        assert qti_item.interaction_type is ExamNetQtiInteractionType.MULTIPLE_RESPONSE
        assert qti_item.correct_choice_identifiers == ("choice_001", "choice_003")

    def test_ai_interpreted_key_maps_its_correct_identifier(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.SINGLE_CHOICE,
            body=text_body("Välj."),
            points=1,
            choices=(
                NativeChoice(choice_id="choice_001", body=plain_body("Ett")),
                NativeChoice(choice_id="choice_002", body=plain_body("Två")),
            ),
            answer_key=NativeAnswerKey(
                origin=NativeAnswerKeyOrigin.AI_INTERPRETED,
                correct_choice_ids=("choice_001",),
            ),
            review=review_complete(),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(document_of((item,)))

        assert qti_item.correct_choice_identifiers == ("choice_001",)

    def test_absent_answer_key_emits_no_correct_identifiers(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.SINGLE_CHOICE,
            body=text_body("Välj."),
            points=1,
            choices=(
                NativeChoice(choice_id="choice_001", body=plain_body("Ett")),
                NativeChoice(choice_id="choice_002", body=plain_body("Två")),
            ),
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT),
            review=review_complete(),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(document_of((item,)))

        assert qti_item.correct_choice_identifiers == ()
