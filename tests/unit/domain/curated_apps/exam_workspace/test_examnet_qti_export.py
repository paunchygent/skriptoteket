"""Mapping tests for the native exam -> Exam.net QTI item adapter."""

import hashlib
from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiEvaluationMode,
    ExamNetQtiInteractionType,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeAssetSegment,
    NativeChoice,
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamItem,
    NativeExamItemKind,
    NativeGap,
    NativeGapSegment,
    NativeItemReview,
    NativeItemReviewState,
    NativeParagraph,
    NativeParseOrigin,
    NativeTextSegment,
)
from skriptoteket.domain.errors import DomainError, ErrorCode

_ASSET_ID = "asset_0123456789abcdef"
_ASSET_PAYLOAD = b"\x89PNG fake payload"


def _review_complete() -> NativeItemReview:
    return NativeItemReview(
        state=NativeItemReviewState.REVIEW_COMPLETE,
        parse_origin=NativeParseOrigin.TEACHER_CREATED,
    )


def _document(
    items: tuple[NativeExamItem, ...],
    assets: tuple[NativeExamAsset, ...] = (),
) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Prov",
        items=items,
        assets=assets,
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def _text_body(text: str) -> tuple[NativeParagraph, ...]:
    return (NativeParagraph(segments=(NativeTextSegment(text=text),)),)


class TestFreeTextMapping:
    def test_free_text_with_points_uses_criterion_points(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.FREE_TEXT,
            title="Fråga 1 (4 p)",
            body=_text_body("Resonera om satsdelar."),
            points=4,
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
            review=_review_complete(),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(_document((item,)))

        assert qti_item.interaction_type is ExamNetQtiInteractionType.FREE_TEXT
        assert qti_item.item_id == "item_001"
        assert qti_item.title == "Fråga 1 (4 p)"
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
            body=_text_body("Resonera fritt."),
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
            review=_review_complete(),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(_document((item,)))

        assert qti_item.evaluation_mode is ExamNetQtiEvaluationMode.MANUAL_UNKEYED
        assert qti_item.free_text_criterion_points is None
        assert qti_item.title == "Fråga 1"


class TestChoiceMapping:
    def test_single_choice_maps_choices_and_correct_identifier(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.SINGLE_CHOICE,
            title="Fråga 1",
            body=_text_body("Välj rätt alternativ."),
            points=2,
            choices=(
                NativeChoice(choice_id="choice_001", text="  Alternativ   ett "),
                NativeChoice(choice_id="choice_002", text="Alternativ två"),
            ),
            answer_key=NativeAnswerKey(
                origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
                correct_choice_ids=("choice_002",),
            ),
            review=_review_complete(),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(_document((item,)))

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
            body=_text_body("Markera alla rätta alternativ."),
            points=3,
            choices=(
                NativeChoice(choice_id="choice_001", text="Ett"),
                NativeChoice(choice_id="choice_002", text="Två"),
                NativeChoice(choice_id="choice_003", text="Tre"),
            ),
            answer_key=NativeAnswerKey(
                origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED,
                correct_choice_ids=("choice_001", "choice_003"),
            ),
            review=_review_complete(),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(_document((item,)))

        assert qti_item.interaction_type is ExamNetQtiInteractionType.MULTIPLE_RESPONSE
        assert qti_item.correct_choice_identifiers == ("choice_001", "choice_003")

    def test_absent_answer_key_emits_no_correct_identifiers(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.SINGLE_CHOICE,
            body=_text_body("Välj."),
            points=1,
            choices=(
                NativeChoice(choice_id="choice_001", text="Ett"),
                NativeChoice(choice_id="choice_002", text="Två"),
            ),
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT),
            review=_review_complete(),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(_document((item,)))

        assert qti_item.correct_choice_identifiers == ()


class TestGapFillMapping:
    def test_gaps_follow_body_placement_order_with_native_gap_ids(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.GAP_FILL,
            body=(
                NativeParagraph(
                    segments=(
                        NativeTextSegment(text="a) Först: "),
                        NativeGapSegment(gap_id="gap_002"),
                    )
                ),
                NativeParagraph(
                    segments=(
                        NativeTextSegment(text="b) Sedan: "),
                        NativeGapSegment(gap_id="gap_001"),
                    )
                ),
            ),
            points=2,
            gaps=(
                NativeGap(gap_id="gap_001", accepted_values=("NF",)),
                NativeGap(gap_id="gap_002", accepted_values=("VF", "verbfras")),
            ),
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED),
            review=_review_complete(),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(_document((item,)))

        assert qti_item.interaction_type is ExamNetQtiInteractionType.GAP_FILL
        assert qti_item.prompt_lines == ("a) Först: [___]", "b) Sedan: [___]")
        assert tuple(gap.response_identifier for gap in qti_item.text_entry_gaps) == (
            "RESPONSE_gap_002",
            "RESPONSE_gap_001",
        )
        assert tuple(gap.label for gap in qti_item.text_entry_gaps) == ("Lucka 1", "Lucka 2")
        assert qti_item.text_entry_gaps[0].accepted_values == ("VF", "verbfras")
        assert qti_item.text_entry_gaps[1].accepted_values == ("NF",)


class TestAssetMapping:
    def _asset_document(self) -> NativeExamDocument:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.FREE_TEXT,
            body=(
                NativeParagraph(
                    segments=(
                        NativeTextSegment(text="Se bilden."),
                        NativeAssetSegment(asset_id=_ASSET_ID),
                    )
                ),
            ),
            points=2,
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
            review=_review_complete(),
        )
        asset = NativeExamAsset(
            asset_id=_ASSET_ID,
            sha256=hashlib.sha256(_ASSET_PAYLOAD).hexdigest(),
            media_type="image/png",
            byte_length=len(_ASSET_PAYLOAD),
        )
        return _document((item,), assets=(asset,))

    def test_referenced_asset_without_payload_raises(self) -> None:
        with pytest.raises(DomainError) as exc_info:
            native_exam_to_examnet_qti_items(self._asset_document())

        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
        assert exc_info.value.details["asset_id"] == _ASSET_ID

    def test_referenced_asset_with_payload_maps_to_image_resource(self) -> None:
        (qti_item,) = native_exam_to_examnet_qti_items(
            self._asset_document(),
            assets_by_id={_ASSET_ID: _ASSET_PAYLOAD},
        )

        (image,) = qti_item.image_resources
        assert image.asset_id == "image_001"
        assert image.filename == "item_001-image-001.png"
        assert image.media_type == "image/png"
        assert image.payload == _ASSET_PAYLOAD
        assert image.source_reference == _ASSET_ID
        assert image.alt_text == "Bild 1 till Fråga 1"
