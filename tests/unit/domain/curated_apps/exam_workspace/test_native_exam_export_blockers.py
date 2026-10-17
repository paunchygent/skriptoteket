"""Export blocker rules for the native exam document (ST-SKRIPT-39-04)."""

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk, DocxMissingImage
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_review import review_source_item
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    item_has_trusted_key,
    native_export_blockers,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
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
)


class TestExportBlockers:
    def test_clean_document_has_no_blockers(self) -> None:
        assert native_export_blockers(make_document(make_gap_fill_item())) == ()

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
