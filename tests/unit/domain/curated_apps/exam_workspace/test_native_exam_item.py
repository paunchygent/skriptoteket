"""Item-level invariants for the native exam document (ST-SKRIPT-39-04)."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
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

    def test_keyed_gap_fill_accepts_gaps_without_accepted_values(self) -> None:
        # An empty gap is a valid draft the export gate refuses (TASK-SKRIPT-40-04-13 U4, L2):
        # this replaces the 40-04-09 R9 save refusal the undo fix needed removed.
        item = make_gap_fill_item(origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED, accepted=())

        assert item.gaps[0].accepted_values == ()

    def test_free_text_requires_not_applicable_origin(self) -> None:
        with pytest.raises(ValidationError, match="not_applicable"):
            NativeExamItem(
                item_id="item_001",
                sequence=1,
                kind=NativeExamItemKind.FREE_TEXT,
                body=(make_paragraph("Fråga"),),
                writing_lines=8,
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
                writing_lines=8,
                body=(
                    NativeParagraph(
                        heading_level=None, segments=(NativeGapSegment(gap_id="gap_001"),)
                    ),
                ),
                answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
                review=make_review(),
            )

    @pytest.mark.parametrize(
        "points", [0, 0.0, 1, 1.25, Decimal("0.00"), Decimal("4.00"), Decimal("1.25")]
    )
    def test_points_accept_finite_nonnegative_numbers(self, points: int | float | Decimal) -> None:
        item = NativeExamItem.model_validate({**dict(make_free_text_item()), "points": points})

        assert item.points == points
        assert NativeExamItem.model_validate_json(item.model_dump_json()).points == points

    @pytest.mark.parametrize(
        ("points", "message"),
        [
            (-1, "non-negative"),
            (-0.25, "non-negative"),
            (Decimal("-0.25"), "non-negative"),
            (float("inf"), "finite"),
            (float("-inf"), "finite"),
            (float("nan"), "finite"),
            (Decimal("Infinity"), "finite"),
            (Decimal("-Infinity"), "finite"),
            (Decimal("NaN"), "finite"),
            (Decimal("sNaN"), "finite"),
            (True, "number"),
            (False, "number"),
            ("0", "number"),
            ("1.25", "number"),
        ],
    )
    def test_points_refuse_negative_nonfinite_boolean_and_text_values(
        self, points: object, message: str
    ) -> None:
        with pytest.raises(ValidationError, match=message):
            NativeExamItem.model_validate({**dict(make_free_text_item()), "points": points})

    def test_free_text_criteria_points_must_equal_the_item_points(self) -> None:
        with pytest.raises(ValidationError, match="equal the item's points"):
            NativeExamItem(
                item_id="item_001",
                sequence=1,
                kind=NativeExamItemKind.FREE_TEXT,
                body=(make_paragraph("Resonera."),),
                writing_lines=8,
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
            writing_lines=8,
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


class TestWritingLines:
    """A free-text question's ruled handwriting lines (W4)."""

    def test_free_text_requires_a_writing_lines_value(self) -> None:
        payload = make_free_text_item().model_dump()
        payload.pop("writing_lines")

        with pytest.raises(ValidationError, match="need writing_lines"):
            NativeExamItem.model_validate(payload)

    @pytest.mark.parametrize("writing_lines", [1, 40])
    def test_writing_lines_accepts_its_bounds(self, writing_lines: int) -> None:
        item = NativeExamItem.model_validate(
            {**make_free_text_item().model_dump(), "writing_lines": writing_lines}
        )

        assert item.writing_lines == writing_lines

    @pytest.mark.parametrize(
        ("writing_lines", "message"),
        [(0, "greater than or equal to 1"), (41, "less than or equal to 40")],
    )
    def test_writing_lines_refuses_out_of_range_values(
        self, writing_lines: int, message: str
    ) -> None:
        with pytest.raises(ValidationError, match=message):
            NativeExamItem.model_validate(
                {**make_free_text_item().model_dump(), "writing_lines": writing_lines}
            )

    def test_writing_lines_refuses_a_boolean(self) -> None:
        with pytest.raises(ValidationError, match="must be an integer"):
            NativeExamItem.model_validate(
                {**make_free_text_item().model_dump(), "writing_lines": True}
            )

    @pytest.mark.parametrize(
        "item",
        [make_single_choice_item(), make_gap_fill_item()],
        ids=["single_choice", "gap_fill"],
    )
    def test_only_free_text_carries_writing_lines(self, item: NativeExamItem) -> None:
        with pytest.raises(ValidationError, match="only free_text items carry writing_lines"):
            NativeExamItem.model_validate({**item.model_dump(), "writing_lines": 8})


class TestEmptyGapDraft:
    """A keyed gap item may hold empty gaps: gap_fill gaps with no accepted
    values, dropdown gaps with no correct option or no options
    (TASK-SKRIPT-40-04-13 U4)."""

    def test_keyed_gap_fill_with_one_empty_gap_among_answered_gaps_is_a_valid_draft(
        self,
    ) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.GAP_FILL,
            body=(
                NativeParagraph(
                    heading_level=None,
                    segments=(
                        NativeTextSegment(text="Vatten kokar vid ", marks=()),
                        NativeGapSegment(gap_id="gap_001"),
                        NativeTextSegment(text=" grader och fryser vid ", marks=()),
                        NativeGapSegment(gap_id="gap_002"),
                        NativeTextSegment(text=" grader.", marks=()),
                    ),
                ),
            ),
            points=1,
            gaps=(
                NativeGap(gap_id="gap_001", accepted_values=("100",)),
                NativeGap(gap_id="gap_002"),
            ),
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED),
            review=make_review(),
        )

        assert [gap.accepted_values for gap in item.gaps] == [("100",), ()]

    def test_keyed_dropdown_with_a_gap_without_correct_option_is_a_valid_draft(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.INLINE_CHOICE,
            body=(
                NativeParagraph(
                    heading_level=None,
                    segments=(
                        NativeTextSegment(text="Välj ", marks=()),
                        NativeGapSegment(gap_id="gap_001"),
                    ),
                ),
            ),
            points=1,
            gaps=(
                NativeGap(
                    gap_id="gap_001",
                    options=(
                        NativeChoice(choice_id="choice_001", body=plain_body("ja")),
                        NativeChoice(choice_id="choice_002", body=plain_body("nej")),
                    ),
                    correct_option_id=None,
                ),
            ),
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED),
            review=make_review(),
        )

        assert item.gaps[0].correct_option_id is None

    def test_keyed_dropdown_with_no_options_is_a_valid_draft(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.INLINE_CHOICE,
            body=(
                NativeParagraph(
                    heading_level=None,
                    segments=(
                        NativeTextSegment(text="Välj ", marks=()),
                        NativeGapSegment(gap_id="gap_001"),
                    ),
                ),
            ),
            points=1,
            gaps=(NativeGap(gap_id="gap_001"),),
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED),
            review=make_review(),
        )

        assert item.gaps[0].options == ()
        assert item.gaps[0].correct_option_id is None
