"""Unit tests for the source-neutral native exam document (ST-SKRIPT-39-04)."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeChoice,
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
    native_exam_document_json_bytes,
    native_export_blockers,
    parse_native_exam_document,
)
from skriptoteket.domain.errors import DomainError, ErrorCode


def _review(
    *,
    state: NativeItemReviewState = NativeItemReviewState.REVIEW_COMPLETE,
    parse_origin: NativeParseOrigin = NativeParseOrigin.DETERMINISTIC,
    confidence: float | None = 0.9,
) -> NativeItemReview:
    return NativeItemReview(
        state=state, parse_origin=parse_origin, confidence=confidence
    )


def _paragraph(text: str) -> NativeParagraph:
    return NativeParagraph(segments=(NativeTextSegment(text=text),))


def _free_text_item(*, sequence: int = 1, item_id: str = "item_001") -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.FREE_TEXT,
        title="Essäfråga",
        body=(_paragraph("Resonera om renässansen."),),
        points=4,
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=_review(),
    )


def _single_choice_item(
    *,
    sequence: int = 1,
    item_id: str = "item_001",
    origin: NativeAnswerKeyOrigin = NativeAnswerKeyOrigin.SOURCE_PROVIDED,
    correct: tuple[str, ...] = ("choice_002",),
) -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.SINGLE_CHOICE,
        title="Flervalsfråga",
        body=(_paragraph("Vilket är huvudordet?"),),
        points=1,
        choices=(
            NativeChoice(choice_id="choice_001", text="vägen"),
            NativeChoice(choice_id="choice_002", text="eleverna"),
        ),
        answer_key=NativeAnswerKey(origin=origin, correct_choice_ids=correct),
        review=_review(),
    )


def _gap_fill_item(
    *,
    sequence: int = 1,
    item_id: str = "item_001",
    accepted: tuple[str, ...] = ("NF",),
    origin: NativeAnswerKeyOrigin = NativeAnswerKeyOrigin.SOURCE_PROVIDED,
) -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.GAP_FILL,
        title="Lucktext",
        body=(
            NativeParagraph(
                segments=(
                    NativeTextSegment(text="Ange frastyp: "),
                    NativeGapSegment(gap_id="gap_001"),
                )
            ),
        ),
        points=2,
        gaps=(NativeGap(gap_id="gap_001", accepted_values=accepted),),
        answer_key=NativeAnswerKey(origin=origin),
        review=_review(),
    )


def _document(*items: NativeExamItem) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Omprov: grammatik",
        items=tuple(items),
        origin=NativeExamDocumentOrigin(kind="created"),
    )


class TestSerializationRoundTrip:
    def test_json_round_trip_preserves_document(self) -> None:
        document = _document(
            _gap_fill_item(sequence=1, item_id="item_001"),
            _single_choice_item(sequence=2, item_id="item_002"),
            _free_text_item(sequence=3, item_id="item_003"),
        )
        payload = native_exam_document_json_bytes(document)
        assert parse_native_exam_document(payload) == document

    def test_serialization_is_deterministic(self) -> None:
        document = _document(_free_text_item())
        assert native_exam_document_json_bytes(
            document
        ) == native_exam_document_json_bytes(document)

    def test_invalid_json_raises_domain_error(self) -> None:
        with pytest.raises(DomainError) as exc_info:
            parse_native_exam_document(b"not json")
        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR

    def test_invalid_payload_raises_domain_error(self) -> None:
        with pytest.raises(DomainError) as exc_info:
            parse_native_exam_document(b'{"schema_version": "native_exam_document_v1"}')
        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


class TestItemInvariants:
    def test_single_choice_requires_exactly_one_correct_choice(self) -> None:
        with pytest.raises(ValidationError, match="exactly one correct"):
            _single_choice_item(correct=("choice_001", "choice_002"))

    def test_choice_item_requires_two_choices(self) -> None:
        with pytest.raises(ValidationError, match="at least two choices"):
            NativeExamItem(
                item_id="item_001",
                sequence=1,
                kind=NativeExamItemKind.SINGLE_CHOICE,
                body=(_paragraph("Fråga"),),
                points=1,
                choices=(NativeChoice(choice_id="choice_001", text="a"),),
                answer_key=NativeAnswerKey(
                    origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
                    correct_choice_ids=("choice_001",),
                ),
                review=_review(),
            )

    def test_correct_choice_ids_must_be_declared(self) -> None:
        with pytest.raises(ValidationError, match="not declared"):
            _single_choice_item(correct=("choice_999",))

    def test_absent_key_must_not_carry_key_data(self) -> None:
        with pytest.raises(ValidationError, match="must not carry key data"):
            _gap_fill_item(origin=NativeAnswerKeyOrigin.ABSENT, accepted=("NF",))

    def test_keyed_gap_fill_requires_accepted_values_per_gap(self) -> None:
        with pytest.raises(ValidationError, match="needs accepted values"):
            _gap_fill_item(
                origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED, accepted=()
            )

    def test_free_text_requires_not_applicable_origin(self) -> None:
        with pytest.raises(ValidationError, match="not_applicable"):
            NativeExamItem(
                item_id="item_001",
                sequence=1,
                kind=NativeExamItemKind.FREE_TEXT,
                body=(_paragraph("Fråga"),),
                answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT),
                review=_review(),
            )

    def test_gap_fill_body_must_place_every_gap(self) -> None:
        with pytest.raises(ValidationError, match="exactly once"):
            NativeExamItem(
                item_id="item_001",
                sequence=1,
                kind=NativeExamItemKind.GAP_FILL,
                body=(_paragraph("Ingen lucka här."),),
                points=1,
                gaps=(NativeGap(gap_id="gap_001", accepted_values=("x",)),),
                answer_key=NativeAnswerKey(
                    origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED
                ),
                review=_review(),
            )

    def test_non_gap_item_must_not_place_gap_segments(self) -> None:
        with pytest.raises(ValidationError, match="only gap_fill"):
            NativeExamItem(
                item_id="item_001",
                sequence=1,
                kind=NativeExamItemKind.FREE_TEXT,
                body=(
                    NativeParagraph(
                        segments=(NativeGapSegment(gap_id="gap_001"),)
                    ),
                ),
                answer_key=NativeAnswerKey(
                    origin=NativeAnswerKeyOrigin.NOT_APPLICABLE
                ),
                review=_review(),
            )

    def test_points_must_be_positive(self) -> None:
        with pytest.raises(ValidationError, match="positive"):
            NativeExamItem(
                item_id="item_001",
                sequence=1,
                kind=NativeExamItemKind.FREE_TEXT,
                body=(_paragraph("Fråga"),),
                points=0,
                answer_key=NativeAnswerKey(
                    origin=NativeAnswerKeyOrigin.NOT_APPLICABLE
                ),
                review=_review(),
            )


class TestDocumentInvariants:
    def test_sequences_must_be_contiguous(self) -> None:
        with pytest.raises(ValidationError, match="contiguous"):
            _document(
                _free_text_item(sequence=1, item_id="item_001"),
                _free_text_item(sequence=3, item_id="item_002"),
            )

    def test_item_ids_must_be_unique(self) -> None:
        with pytest.raises(ValidationError, match="unique"):
            _document(
                _free_text_item(sequence=1, item_id="item_001"),
                _free_text_item(sequence=2, item_id="item_001"),
            )

    def test_docx_import_origin_requires_source_fields(self) -> None:
        with pytest.raises(ValidationError, match="docx_import origin requires"):
            NativeExamDocumentOrigin(kind="docx_import")


class TestMutationHelpers:
    def test_next_item_id_advances_past_highest(self) -> None:
        document = _document(
            _free_text_item(sequence=1, item_id="item_001"),
            _free_text_item(sequence=2, item_id="item_007"),
        )
        assert document.next_item_id() == "item_008"

    def test_appended_item_must_take_next_sequence(self) -> None:
        document = _document(_free_text_item())
        with pytest.raises(DomainError) as exc_info:
            document.with_appended_item(
                _free_text_item(sequence=5, item_id="item_002")
            )
        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR

    def test_append_and_replace_round_trip(self) -> None:
        document = _document(_free_text_item())
        appended = document.with_appended_item(
            _single_choice_item(sequence=2, item_id="item_002")
        )
        assert [item.item_id for item in appended.items] == ["item_001", "item_002"]
        replacement = _single_choice_item(
            sequence=2, item_id="item_002", correct=("choice_001",)
        )
        replaced = appended.with_replaced_item(replacement)
        assert replaced.item_by_id("item_002").answer_key.correct_choice_ids == (
            "choice_001",
        )

    def test_replace_cannot_change_sequence(self) -> None:
        document = _document(_free_text_item())
        with pytest.raises(DomainError):
            document.with_replaced_item(
                _free_text_item(sequence=2, item_id="item_001")
            )

    def test_revision_must_advance_by_one(self) -> None:
        document = _document(_free_text_item())
        assert document.with_revision(2).revision == 2
        with pytest.raises(DomainError) as exc_info:
            document.with_revision(5)
        assert exc_info.value.code is ErrorCode.CONFLICT


class TestExportBlockers:
    def test_clean_document_has_no_blockers(self) -> None:
        assert native_export_blockers(_document(_gap_fill_item())) == ()

    def test_review_required_blocks_export(self) -> None:
        item = _gap_fill_item().model_copy(
            update={
                "review": _review(
                    state=NativeItemReviewState.REVIEW_REQUIRED,
                    parse_origin=NativeParseOrigin.LLM_PARSED,
                    confidence=0.4,
                )
            }
        )
        reasons = {
            blocker.reason for blocker in native_export_blockers(_document(item))
        }
        assert "review_required" in reasons

    def test_machine_proposed_key_blocks_export(self) -> None:
        item = _single_choice_item(
            origin=NativeAnswerKeyOrigin.MACHINE_PROPOSED
        )
        reasons = {
            blocker.reason for blocker in native_export_blockers(_document(item))
        }
        assert "machine_proposed_key_unreviewed" in reasons

    def test_missing_points_blocks_export(self) -> None:
        item = _free_text_item().model_copy(update={"points": None})
        reasons = {
            blocker.reason for blocker in native_export_blockers(_document(item))
        }
        assert "missing_points" in reasons
