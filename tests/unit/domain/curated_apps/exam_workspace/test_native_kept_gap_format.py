"""Kept-answer links on text runs and kept gaps on gap items (TASK-SKRIPT-40-04-13 H1).

A reverted gap keeps its other answers hidden on the word: the word's text run
carries ``kept_gap_id`` and the item carries the matching ``NativeGap`` in
``kept_gaps``. The link is not a mark, renderers read the word as plain text,
and kept gaps never count as gaps of the question.
"""

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.digiexam_body import digiexam_body
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
    validate_text_only_body,
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
    make_review,
)


def kept_run(text: str, gap_id: str = "gap_002") -> NativeTextSegment:
    return NativeTextSegment(text=text, marks=(), kept_gap_id=gap_id)


def _option(choice_id: str, text: str) -> dict[str, object]:
    return {
        "choice_id": choice_id,
        "body": [
            {
                "heading_level": None,
                "segments": [{"kind": "text", "text": text, "marks": []}],
            }
        ],
    }


def kept_gap_fill_item(
    *,
    kept_gaps: tuple[NativeGap, ...] = (
        NativeGap(gap_id="gap_002", accepted_values=("nominalfras", "NF")),
    ),
    accepted: tuple[str, ...] = ("VF",),
    origin: NativeAnswerKeyOrigin = NativeAnswerKeyOrigin.SOURCE_PROVIDED,
) -> NativeExamItem:
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.GAP_FILL,
        body=(
            NativeParagraph(
                heading_level=None,
                segments=(
                    NativeTextSegment(text="Ange frastyp: ", marks=()),
                    NativeGapSegment(gap_id="gap_001"),
                    NativeTextSegment(text=" Ordet ", marks=()),
                    kept_run("nominalfras"),
                    NativeTextSegment(text=" kvar.", marks=()),
                ),
            ),
        ),
        points=2,
        gaps=(NativeGap(gap_id="gap_001", accepted_values=accepted),),
        kept_gaps=kept_gaps,
        answer_key=NativeAnswerKey(origin=origin),
        review=make_review(),
    )


class TestKeptGapIdOnTextRuns:
    def test_defaults_to_none_on_ordinary_text(self) -> None:
        assert NativeTextSegment(text="ord", marks=()).kept_gap_id is None

    def test_accepts_gap_id_shape(self) -> None:
        assert kept_run("ord").kept_gap_id == "gap_002"

    @pytest.mark.parametrize("gap_id", ["lucka", "gap_1", "gap_0001", " gap_002", ""])
    def test_refuses_non_gap_ids(self, gap_id: str) -> None:
        with pytest.raises(ValidationError, match="kept_gap_id"):
            NativeTextSegment(text="ord", marks=(), kept_gap_id=gap_id)

    def test_is_not_a_mark(self) -> None:
        with pytest.raises(ValidationError):
            NativeTextSegment.model_validate(
                {"kind": "text", "text": "ord", "marks": ["kept_gap_id"]}
            )

    def test_marks_still_canonicalise_with_a_kept_link(self) -> None:
        segment = NativeTextSegment(text="ord", marks=("underline", "bold"), kept_gap_id="gap_002")

        assert segment.marks == ("bold", "underline")
        assert segment.kept_gap_id == "gap_002"

    def test_superscript_subscript_exclusion_still_applies_with_a_kept_link(self) -> None:
        with pytest.raises(ValidationError, match="superscript and subscript"):
            NativeTextSegment(
                text="ord",
                marks=("superscript", "subscript"),
                kept_gap_id="gap_002",
            )

    def test_runs_differing_only_in_kept_link_are_not_equal(self) -> None:
        """Neighbouring runs merge only when marks and kept links match on both sides."""
        plain = NativeTextSegment(text="ord", marks=())
        linked = NativeTextSegment(text="ord", marks=(), kept_gap_id="gap_002")
        other_link = NativeTextSegment(text="ord", marks=(), kept_gap_id="gap_003")

        assert plain != linked
        assert linked != other_link
        assert linked == kept_run("ord")
        assert hash(plain) != hash(linked)


class TestKeptLinksOutsideItemBodiesAreRefused:
    def test_choice_body_refuses_kept_links(self) -> None:
        with pytest.raises(ValidationError, match="kept"):
            NativeChoice(
                choice_id="choice_001",
                body=(NativeParagraph(heading_level=None, segments=(kept_run("ord"),)),),
            )

    def test_text_only_body_refuses_kept_links(self) -> None:
        with pytest.raises(ValueError, match="kept gap link"):
            validate_text_only_body(
                (NativeParagraph(heading_level=None, segments=(kept_run("ord"),)),),
                surface="match entry",
            )

    def test_digiexam_import_never_sets_the_field(self) -> None:
        body = digiexam_body(
            html="<p>Frasen <b>är</b> nominalfras.</p>",
            lines=(),
            image_ids={},
            gap_ids={},
        )
        assert body
        for paragraph in body:
            for segment in paragraph.segments:
                assert isinstance(segment, NativeTextSegment)
                assert segment.kept_gap_id is None


class TestKeptGapInvariants:
    def test_accepts_linked_kept_gap(self) -> None:
        item = kept_gap_fill_item()

        assert item.kept_gaps[0].gap_id == "gap_002"
        assert item.body_gaps() == (item.gaps[0],)

    def test_refuses_kept_gap_without_any_run(self) -> None:
        payload = kept_gap_fill_item().model_dump(mode="json")
        payload["body"] = [
            {
                "heading_level": None,
                "segments": [
                    {"kind": "text", "text": "Ingen länk.", "marks": []},
                    {"kind": "gap", "gap_id": "gap_001"},
                ],
            }
        ]
        with pytest.raises(ValidationError, match="kept gap gap_002 has no text run"):
            NativeExamItem.model_validate(payload)

    def test_refuses_run_naming_an_unknown_kept_gap(self) -> None:
        with pytest.raises(ValidationError, match="names no kept gap"):
            kept_gap_fill_item(kept_gaps=())

    def test_refuses_duplicate_kept_gap_ids(self) -> None:
        item = kept_gap_fill_item()
        payload = item.model_dump(mode="json")
        payload["kept_gaps"] = [payload["kept_gaps"][0], payload["kept_gaps"][0]]
        with pytest.raises(ValidationError, match="kept gap ids must be unique"):
            NativeExamItem.model_validate(payload)

    def test_refuses_kept_gap_id_colliding_with_a_live_gap_id(self) -> None:
        item = kept_gap_fill_item()
        payload = item.model_dump(mode="json")
        payload["kept_gaps"] = [{"gap_id": "gap_001", "accepted_values": ["VF"]}]
        with pytest.raises(ValidationError, match="distinct from the item's gaps"):
            NativeExamItem.model_validate(payload)

    @pytest.mark.parametrize(
        "kind",
        [
            NativeExamItemKind.FREE_TEXT,
            NativeExamItemKind.SINGLE_CHOICE,
            NativeExamItemKind.MULTIPLE_RESPONSE,
            NativeExamItemKind.MATCHING,
            NativeExamItemKind.ORDERING,
        ],
    )
    def test_only_gap_kinds_carry_kept_gaps(self, kind: NativeExamItemKind) -> None:
        item = kept_gap_fill_item()
        payload = item.model_dump(mode="json")
        payload["kind"] = kind.value
        with pytest.raises(ValidationError, match="only gap_fill and inline_choice"):
            NativeExamItem.model_validate(payload)

    def test_kept_gap_without_accepted_values_is_not_a_key_gap(self) -> None:
        """Kept gaps stay out of the answer-key invariants: a keyed item whose kept
        gap carries no accepted values still validates, while a live gap without
        any would not."""
        item = kept_gap_fill_item(
            kept_gaps=(NativeGap(gap_id="gap_002"),),
        )

        assert item.kept_gaps[0].accepted_values == ()

    def test_absent_key_ignores_answered_kept_gaps(self) -> None:
        item = kept_gap_fill_item(accepted=(), origin=NativeAnswerKeyOrigin.ABSENT)

        assert item.answer_key.origin is NativeAnswerKeyOrigin.ABSENT

    def test_kept_gaps_follow_gap_shape_rules_for_gap_fill(self) -> None:
        with pytest.raises(ValidationError, match="only inline_choice gaps carry options"):
            kept_gap_fill_item(
                kept_gaps=(
                    NativeGap(
                        gap_id="gap_002",
                        options=(
                            NativeChoice(
                                choice_id="choice_001",
                                body=(
                                    NativeParagraph(
                                        heading_level=None,
                                        segments=(NativeTextSegment(text="NF", marks=()),),
                                    ),
                                ),
                            ),
                        ),
                        correct_option_id="choice_001",
                    ),
                )
            )

    def test_inline_choice_kept_gap_needs_its_option_list(self) -> None:
        item = kept_gap_fill_item()
        payload = item.model_dump(mode="json")
        payload.update(
            kind="inline_choice",
            gaps=[
                {
                    "gap_id": "gap_001",
                    "options": [
                        _option("choice_001", "VF"),
                        _option("choice_002", "NF"),
                    ],
                    "correct_option_id": "choice_001",
                }
            ],
            kept_gaps=[
                {
                    "gap_id": "gap_002",
                    "options": [_option("choice_001", "ord")],
                    "correct_option_id": "choice_001",
                }
            ],
        )
        assert NativeExamItem.model_validate(payload).kept_gaps[0].correct_option_id == "choice_001"

        payload["kept_gaps"] = [{"gap_id": "gap_002"}]
        with pytest.raises(ValidationError, match="need an option list"):
            NativeExamItem.model_validate(payload)

    def test_json_round_trip_keeps_the_link(self) -> None:
        item = kept_gap_fill_item()

        restored = NativeExamItem.model_validate_json(item.model_dump_json())

        assert restored == item
        kept_segment = restored.body[0].segments[3]
        assert isinstance(kept_segment, NativeTextSegment)
        assert kept_segment.kept_gap_id == "gap_002"
