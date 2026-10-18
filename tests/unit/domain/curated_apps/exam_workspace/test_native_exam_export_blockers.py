"""Export blocker rules for the native exam document (ST-SKRIPT-39-04)."""

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk, DocxMissingImage
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_review import review_source_item
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    INLINE_CHOICE_MIN_OPTIONS,
    NativeExportBlocker,
    item_has_trusted_key,
    native_export_blockers,
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
    NativeItemReviewState,
    NativeParseOrigin,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
    make_gap_fill_item,
    make_review,
    make_single_choice_item,
    plain_body,
)


class TestExportBlockers:
    def test_clean_document_has_no_blockers(self) -> None:
        assert native_export_blockers(make_document(make_gap_fill_item())) == ()

    @pytest.mark.parametrize("title", ["?!...", "", "  ", " - / ", "\u0301", "(…)"])
    def test_a_title_without_letters_or_digits_blocks_the_exam_not_a_question(
        self, title: str
    ) -> None:
        document = make_document(make_gap_fill_item()).model_copy(update={"title": title})
        assert native_export_blockers(document) == (
            NativeExportBlocker(item_id=None, reason="title_without_text"),
        )

    @pytest.mark.parametrize("title", ["Prov 1", "1", "å", "?! Prov", "²"])
    def test_a_title_with_one_letter_or_digit_does_not_block(self, title: str) -> None:
        document = make_document(make_gap_fill_item()).model_copy(update={"title": title})
        assert native_export_blockers(document) == ()

    def test_a_converted_item_that_needs_review_with_points_and_key_does_not_block(
        self,
    ) -> None:
        item = make_gap_fill_item().model_copy(
            update={
                "review": make_review(
                    state=NativeItemReviewState.REVIEW_REQUIRED,
                    parse_origin=NativeParseOrigin.LLM_PARSED,
                    confidence=0.4,
                )
            }
        )
        assert item.points is not None
        assert native_export_blockers(make_document(item)) == ()

    def test_an_unbuilt_question_blocks_until_marked_reviewed(self) -> None:
        unbuilt = make_gap_fill_item().model_copy(
            update={
                "points": 2,
                "points_estimated": True,
                "review": make_review(
                    state=NativeItemReviewState.REVIEW_REQUIRED,
                    parse_origin=NativeParseOrigin.SOURCE_FALLBACK,
                ),
            }
        )
        reasons = [blocker.reason for blocker in native_export_blockers(make_document(unbuilt))]
        assert reasons == ["unbuilt_question"]

        review = unbuilt.review.model_copy(update={"state": NativeItemReviewState.REVIEW_COMPLETE})
        reviewed = unbuilt.model_copy(update={"review": review})
        assert native_export_blockers(make_document(reviewed)) == ()

    @pytest.mark.parametrize("missing_picture", [False, True])
    def test_docx_source_fallback_blocks_without_retry_or_import_metadata(
        self, missing_picture: bool
    ) -> None:
        chunk = DocxChunk(
            anchor="body:0001",
            kind="paragraph",
            text="Förklara. (2 p)",
            marked_text="Förklara. (2 p)",
            missing_images=(DocxMissingImage("/word/media/figur.emf", "image/x-emf"),)
            if missing_picture
            else (),
        )
        item = review_source_item((chunk,), "Frågan kunde inte konverteras.")
        assert item.points == 2
        assert item.retry_source is None
        assert item.import_record is None
        # The explicit marker, not an anchor or metadata, identifies the fallback.
        item = item.model_copy(update={"source_anchor": None})
        assert [blocker.reason for blocker in native_export_blockers(make_document(item))] == [
            "unbuilt_question"
        ]
        reviewed = item.model_copy(
            update={
                "review": item.review.model_copy(
                    update={"state": NativeItemReviewState.REVIEW_COMPLETE}
                )
            }
        )
        assert native_export_blockers(make_document(reviewed)) == ()

    def test_estimated_points_require_points(self) -> None:
        with pytest.raises(ValidationError, match="estimated points require points"):
            NativeExamItem.model_validate(
                {**make_gap_fill_item().model_dump(), "points": None, "points_estimated": True}
            )

    def test_machine_proposed_key_blocks_export(self) -> None:
        item = make_single_choice_item(origin=NativeAnswerKeyOrigin.MACHINE_PROPOSED)
        reasons = {blocker.reason for blocker in native_export_blockers(make_document(item))}
        assert "machine_proposed_key_unreviewed" in reasons

    def test_ai_interpreted_key_is_trusted_and_does_not_block_export(self) -> None:
        item = make_single_choice_item(origin=NativeAnswerKeyOrigin.AI_INTERPRETED)

        assert item_has_trusted_key(item)
        assert native_export_blockers(make_document(item)) == ()

    def test_machine_proposed_key_is_not_trusted(self) -> None:
        item = make_single_choice_item(origin=NativeAnswerKeyOrigin.MACHINE_PROPOSED)

        assert not item_has_trusted_key(item)

    @pytest.mark.parametrize(
        "kind",
        [
            NativeExamItemKind.SINGLE_CHOICE,
            NativeExamItemKind.MULTIPLE_RESPONSE,
            NativeExamItemKind.GAP_FILL,
        ],
    )
    def test_absent_answer_key_on_keyed_item_blocks_export(self, kind: NativeExamItemKind) -> None:
        if kind is NativeExamItemKind.GAP_FILL:
            item = make_gap_fill_item(origin=NativeAnswerKeyOrigin.ABSENT, accepted=())
        else:
            item = make_single_choice_item(origin=NativeAnswerKeyOrigin.ABSENT, correct=())
            item = NativeExamItem.model_validate({**item.model_dump(), "kind": kind})

        blockers = native_export_blockers(make_document(item))

        assert [(blocker.item_id, blocker.reason) for blocker in blockers] == [
            ("item_001", "missing_answer_key")
        ]

    def test_free_text_item_needs_no_answer_key(self) -> None:
        assert native_export_blockers(make_document(make_free_text_item())) == ()

    def test_missing_points_blocks_export(self) -> None:
        item = make_free_text_item().model_copy(update={"points": None})
        reasons = {blocker.reason for blocker in native_export_blockers(make_document(item))}
        assert "missing_points" in reasons


def _dropdown_gap(gap_id: str, option_texts: tuple[str, ...]) -> NativeGap:
    options = tuple(
        NativeChoice(choice_id=f"choice_{index:03d}", body=plain_body(text))
        for index, text in enumerate(option_texts, start=1)
    )
    return NativeGap(gap_id=gap_id, options=options, correct_option_id="choice_001")


def _dropdown_item(*gaps: NativeGap) -> NativeExamItem:
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.INLINE_CHOICE,
        body=tuple(
            NativeParagraph(heading_level=None, segments=(NativeGapSegment(gap_id=gap.gap_id),))
            for gap in gaps
        ),
        points=1,
        gaps=gaps,
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED),
        review=make_review(),
    )


def _reasons(item: NativeExamItem) -> list[str]:
    return [blocker.reason for blocker in native_export_blockers(make_document(item))]


class TestTooFewGapOptions:
    def test_threshold_is_the_published_minimum(self) -> None:
        def reasons_for(option_count: int) -> list[str]:
            gap = _dropdown_gap("gap_001", tuple(f"alt{n}" for n in range(option_count)))
            return _reasons(_dropdown_item(gap))

        assert reasons_for(INLINE_CHOICE_MIN_OPTIONS - 1) == ["too_few_gap_options"]
        assert reasons_for(INLINE_CHOICE_MIN_OPTIONS) == []

    def test_one_option_blocks_and_two_do_not(self) -> None:
        assert _reasons(_dropdown_item(_dropdown_gap("gap_001", ("a",)))) == ["too_few_gap_options"]
        assert _reasons(_dropdown_item(_dropdown_gap("gap_001", ("a", "b")))) == []

    def test_one_blocker_per_item_even_when_several_gaps_are_short(self) -> None:
        item = _dropdown_item(
            _dropdown_gap("gap_001", ("a",)),
            _dropdown_gap("gap_002", ("a", "b")),
            _dropdown_gap("gap_003", ("a",)),
        )
        assert _reasons(item) == ["too_few_gap_options"]

    def test_gap_fill_item_never_gets_it(self) -> None:
        assert "too_few_gap_options" not in _reasons(make_gap_fill_item())

    def test_single_empty_option_blocks_for_both_reasons(self) -> None:
        assert _reasons(_dropdown_item(_dropdown_gap("gap_001", (" ",)))) == [
            "empty_gap_option",
            "too_few_gap_options",
        ]
