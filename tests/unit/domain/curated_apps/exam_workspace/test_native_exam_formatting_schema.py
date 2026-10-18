"""Schema tests for source formatting on native choice bodies (TASK-SKRIPT-39-09-08)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NATIVE_TEXT_MARK_ORDER,
    NativeAssetSegment,
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_matching import (
    NativeMatchLeft,
    NativeMatchRight,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import NativeChoice

pytestmark = pytest.mark.unit

_ASSET_ID = "asset_0123456789abcdef"


def _paragraph(segment: object, *, heading_level: int | None = None) -> NativeParagraph:
    return NativeParagraph(segments=(segment,), heading_level=heading_level)


class TestTextMarks:
    def test_marks_are_required(self) -> None:
        with pytest.raises(ValidationError, match="marks"):
            NativeTextSegment.model_validate({"text": "ord"})

    def test_marks_are_canonicalized_to_the_fixed_order(self) -> None:
        segment = NativeTextSegment(text="ord", marks=["subscript", "bold", "italic"])

        assert segment.marks == ("bold", "italic", "subscript")
        assert segment.marks == tuple(
            mark for mark in NATIVE_TEXT_MARK_ORDER if mark in segment.marks
        )

    def test_empty_marks_are_an_explicit_empty_tuple(self) -> None:
        assert NativeTextSegment(text="ord", marks=()).marks == ()

    def test_a_repeated_mark_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="must not repeat"):
            NativeTextSegment(text="ord", marks=["bold", "bold"])

    def test_superscript_and_subscript_together_are_rejected(self) -> None:
        with pytest.raises(ValidationError, match="superscript and subscript"):
            NativeTextSegment(text="ord", marks=["superscript", "subscript"])

    def test_an_unknown_mark_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            NativeTextSegment(text="ord", marks=["blink"])

    def test_gap_and_asset_segments_carry_no_marks_field(self) -> None:
        assert "marks" not in NativeGapSegment.model_fields
        assert "marks" not in NativeAssetSegment.model_fields


class TestParagraphHeadingLevels:
    def test_heading_level_is_required(self) -> None:
        with pytest.raises(ValidationError, match="heading_level"):
            NativeParagraph.model_validate({"segments": (NativeTextSegment(text="ord", marks=()),)})

    def test_heading_level_accepts_none_and_one_to_three(self) -> None:
        for level in (None, 1, 2, 3):
            paragraph = _paragraph(NativeTextSegment(text="ord", marks=()), heading_level=level)

            assert paragraph.heading_level == level

    def test_heading_level_outside_one_to_three_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _paragraph(NativeTextSegment(text="ord", marks=()), heading_level=4)


class TestChoiceBodies:
    def test_choice_requires_a_body_and_has_no_text_reader(self) -> None:
        with pytest.raises(ValidationError):
            NativeChoice.model_validate({"choice_id": "choice_001", "text": "vägen"})

        choice = NativeChoice(
            choice_id="choice_001",
            body=(
                _paragraph(NativeTextSegment(text="vägen", marks=("bold",)), heading_level=None),
            ),
        )

        segment = choice.body[0].segments[0]
        assert isinstance(segment, NativeTextSegment)
        assert segment.marks == ("bold",)
        assert not hasattr(choice, "text")

    def test_choice_body_may_be_empty_while_the_teacher_edits(self) -> None:
        assert NativeChoice(choice_id="choice_001", body=()).body == ()

    def test_choice_body_rejects_a_gap_segment(self) -> None:
        with pytest.raises(ValidationError, match="choice body carries text"):
            NativeChoice(
                choice_id="choice_001",
                body=(_paragraph(NativeGapSegment(gap_id="gap_001"), heading_level=None),),
            )

    def test_choice_body_rejects_an_asset_segment(self) -> None:
        with pytest.raises(ValidationError, match="choice body carries text"):
            NativeChoice(
                choice_id="choice_001",
                body=(_paragraph(NativeAssetSegment(asset_id=_ASSET_ID), heading_level=None),),
            )


class TestMatchEntryBodies:
    def test_match_entries_require_a_body(self) -> None:
        with pytest.raises(ValidationError):
            NativeMatchLeft.model_validate({"left_id": "left_001", "text": "A"})
        with pytest.raises(ValidationError):
            NativeMatchRight.model_validate({"right_id": "right_001", "text": "B"})

    def test_match_entries_keep_marks_and_heading_levels(self) -> None:
        segment = NativeTextSegment(text="A", marks=("underline",))
        left = NativeMatchLeft(left_id="left_001", body=(_paragraph(segment, heading_level=3),))
        right = NativeMatchRight(right_id="right_001", body=(_paragraph(segment),))

        right_segment = right.body[0].segments[0]
        assert isinstance(right_segment, NativeTextSegment)
        assert left.body[0].heading_level == 3
        assert right_segment.marks == ("underline",)
        assert not hasattr(left, "text")
        assert not hasattr(right, "text")

    def test_match_entry_body_rejects_a_gap_segment(self) -> None:
        with pytest.raises(ValidationError, match="match entry body carries text"):
            NativeMatchLeft(
                left_id="left_001",
                body=(_paragraph(NativeGapSegment(gap_id="gap_001"), heading_level=None),),
            )
