"""Item-level invariants for the native exam document (ST-SKRIPT-39-04)."""

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_criteria import (
    NativeExamCriterion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
    NativeGap,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
    make_gap_fill_item,
    make_paragraph,
    make_review,
    make_single_choice_item,
    plain_body,
)


class TestItemInvariants:
    def test_single_choice_requires_exactly_one_correct_choice(self) -> None:
        with pytest.raises(ValidationError, match="exactly one correct"):
            make_single_choice_item(correct=("choice_001", "choice_002"))

    def test_choice_item_requires_two_choices(self) -> None:
        with pytest.raises(ValidationError, match="at least two choices"):
            NativeExamItem(
                item_id="item_001",
                sequence=1,
                kind=NativeExamItemKind.SINGLE_CHOICE,
                body=(make_paragraph("Fråga"),),
                points=1,
                choices=(NativeChoice(choice_id="choice_001", body=plain_body("a")),),
                answer_key=NativeAnswerKey(
                    origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
                    correct_choice_ids=("choice_001",),
                ),
                review=make_review(),
            )

    def test_correct_choice_ids_must_be_declared(self) -> None:
        with pytest.raises(ValidationError, match="not declared"):
            make_single_choice_item(correct=("choice_999",))

    def test_absent_key_must_not_carry_key_data(self) -> None:
        with pytest.raises(ValidationError, match="must not carry key data"):
            make_gap_fill_item(origin=NativeAnswerKeyOrigin.ABSENT, accepted=("NF",))

    def test_keyed_gap_fill_requires_accepted_values_per_gap(self) -> None:
        with pytest.raises(ValidationError, match="needs accepted values"):
            make_gap_fill_item(origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED, accepted=())

    def test_free_text_requires_not_applicable_origin(self) -> None:
        with pytest.raises(ValidationError, match="not_applicable"):
            NativeExamItem(
                item_id="item_001",
                sequence=1,
                kind=NativeExamItemKind.FREE_TEXT,
                body=(make_paragraph("Fråga"),),
                answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT),
                review=make_review(),
            )

    def test_gap_fill_body_must_place_every_gap(self) -> None:
        with pytest.raises(ValidationError, match="exactly once"):
            NativeExamItem(
                item_id="item_001",
                sequence=1,
                kind=NativeExamItemKind.GAP_FILL,
                body=(make_paragraph("Ingen lucka här."),),
                points=1,
                gaps=(NativeGap(gap_id="gap_001", accepted_values=("x",)),),
                answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED),
                review=make_review(),
            )

    def test_non_gap_item_must_not_place_gap_segments(self) -> None:
        with pytest.raises(ValidationError, match="only gap_fill"):
            NativeExamItem(
                item_id="item_001",
                sequence=1,
                kind=NativeExamItemKind.FREE_TEXT,
                body=(
                    NativeParagraph(
                        heading_level=None, segments=(NativeGapSegment(gap_id="gap_001"),)
                    ),
                ),
                answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
                review=make_review(),
            )

    def test_points_must_be_positive(self) -> None:
        with pytest.raises(ValidationError, match="positive"):
            NativeExamItem(
                item_id="item_001",
                sequence=1,
                kind=NativeExamItemKind.FREE_TEXT,
                body=(make_paragraph("Fråga"),),
                points=0,
                answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
                review=make_review(),
            )

    def test_free_text_criteria_points_must_equal_the_item_points(self) -> None:
        with pytest.raises(ValidationError, match="equal the item's points"):
            NativeExamItem(
                item_id="item_001",
                sequence=1,
                kind=NativeExamItemKind.FREE_TEXT,
                body=(make_paragraph("Resonera."),),
                points=3,
                criteria=(
                    NativeExamCriterion(text="Ett korrekt exempel.", points=2),
                    NativeExamCriterion(text="En korrekt förklaring.", points=2),
                ),
                answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
                review=make_review(),
            )

    def test_free_text_criteria_equal_to_the_item_points_are_valid(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.FREE_TEXT,
            body=(make_paragraph("Resonera."),),
            points=3,
            criteria=(
                NativeExamCriterion(text="Ett korrekt exempel.", points=2),
                NativeExamCriterion(text="En korrekt förklaring.", points=1),
            ),
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
            review=make_review(),
        )

        assert item.points == sum(criterion.points for criterion in item.criteria)

    def test_a_non_free_text_item_must_not_carry_criteria(self) -> None:
        with pytest.raises(ValidationError, match="only free_text items carry criteria"):
            NativeExamItem(
                item_id="item_001",
                sequence=1,
                kind=NativeExamItemKind.SINGLE_CHOICE,
                body=(make_paragraph("Fråga"),),
                points=2,
                choices=(
                    NativeChoice(choice_id="choice_001", body=plain_body("a")),
                    NativeChoice(choice_id="choice_002", body=plain_body("b")),
                ),
                criteria=(NativeExamCriterion(text="Kriterium", points=2),),
                answer_key=NativeAnswerKey(
                    origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
                    correct_choice_ids=("choice_001",),
                ),
                review=make_review(),
            )

    @pytest.mark.parametrize("text", ["", "   "])
    def test_criterion_text_must_be_non_empty(self, text: str) -> None:
        with pytest.raises(ValidationError, match="at least 1 character|must be non-empty"):
            NativeExamCriterion(text=text, points=1)

    def test_criterion_points_must_be_whole_and_at_least_one(self) -> None:
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            NativeExamCriterion(text="Kriterium", points=0)
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            NativeExamCriterion(text="Kriterium", points=-1)
        with pytest.raises(ValidationError, match="valid integer"):
            NativeExamCriterion(text="Kriterium", points=1.5)
        with pytest.raises(ValidationError, match="whole number"):
            NativeExamCriterion(text="Kriterium", points=True)

    def test_a_saved_marking_guide_has_no_reader(self) -> None:
        with pytest.raises(ValidationError, match="marking_guide"):
            NativeExamItem.model_validate(
                {**make_free_text_item().model_dump(), "marking_guide": "Gammal rättningsmall."}
            )
