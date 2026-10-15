"""Unit tests for the source-neutral native exam document (ST-SKRIPT-39-04)."""

import json
from decimal import Decimal
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
    NativeMatchLeft,
    NativeMatchPair,
    NativeMatchRight,
    NativeParagraph,
    NativeParseOrigin,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_json import (
    native_exam_document_json_bytes,
    parse_native_exam_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    item_has_trusted_key,
    native_export_blockers,
)
from skriptoteket.domain.errors import DomainError, ErrorCode


def _review(
    *,
    state: NativeItemReviewState = NativeItemReviewState.REVIEW_COMPLETE,
    parse_origin: NativeParseOrigin = NativeParseOrigin.DETERMINISTIC,
    confidence: float | None = 0.9,
) -> NativeItemReview:
    return NativeItemReview(state=state, parse_origin=parse_origin, confidence=confidence)


def _paragraph(text: str) -> NativeParagraph:
    return NativeParagraph(segments=(NativeTextSegment(text=text),))


def _free_text_item(*, sequence: int = 1, item_id: str = "item_001") -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.FREE_TEXT,
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
    automatic: tuple[str, ...] = (),
    facit_text: str | None = None,
) -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.GAP_FILL,
        facit_text=facit_text,
        body=(
            NativeParagraph(
                segments=(
                    NativeTextSegment(text="Ange frastyp: "),
                    NativeGapSegment(gap_id="gap_001"),
                )
            ),
        ),
        points=2,
        gaps=(
            NativeGap(
                gap_id="gap_001",
                accepted_values=accepted,
                automatic_values=automatic,
            ),
        ),
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


_MATCH_RIGHT_TEXT = {
    "right_001": "däggdjur",
    "right_002": "fåglar",
    "right_003": "fiskar",
    "right_004": "kräldjur",
}


def _matching_item(
    *,
    sequence: int = 1,
    item_id: str = "item_001",
    pairs: tuple[tuple[str, str], ...] = (
        ("left_001", "right_001"),
        ("left_002", "right_002"),
        ("left_003", "right_003"),
    ),
    match_right: tuple[str, ...] = ("right_001", "right_002", "right_003"),
    tick_points: Decimal | None = Decimal("1"),
    points: int | float | None = 3,
    origin: NativeAnswerKeyOrigin = NativeAnswerKeyOrigin.SOURCE_PROVIDED,
) -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.MATCHING,
        body=(_paragraph("Kategorisera orden i rätt ordklass."),),
        points=points,
        tick_points=tick_points,
        match_left=(
            NativeMatchLeft(left_id="left_001", text="hund"),
            NativeMatchLeft(left_id="left_002", text="katt"),
            NativeMatchLeft(left_id="left_003", text="fågel"),
        ),
        match_right=tuple(
            NativeMatchRight(right_id=right_id, text=_MATCH_RIGHT_TEXT[right_id])
            for right_id in match_right
        ),
        answer_key=NativeAnswerKey(
            origin=origin,
            match_pairs=tuple(
                NativeMatchPair(left_id=left_id, right_id=right_id) for left_id, right_id in pairs
            ),
        ),
        review=_review(),
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
        assert native_exam_document_json_bytes(document) == native_exam_document_json_bytes(
            document
        )

    def test_invalid_json_raises_domain_error(self) -> None:
        with pytest.raises(DomainError) as exc_info:
            parse_native_exam_document(b"not json")
        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR

    def test_invalid_payload_raises_domain_error(self) -> None:
        with pytest.raises(DomainError) as exc_info:
            parse_native_exam_document(b'{"schema_version": "native_exam_document_v1"}')
        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR

    def test_document_declares_the_v2_schema(self) -> None:
        assert _document(_free_text_item()).schema_version == "native_exam_document_v2"

    def test_saved_v1_payload_has_no_compatibility_reader(self) -> None:
        document = _document(_free_text_item())
        payload = json.loads(native_exam_document_json_bytes(document))
        payload["schema_version"] = "native_exam_document_v1"

        with pytest.raises(DomainError) as exc_info:
            parse_native_exam_document(json.dumps(payload).encode("utf-8"))

        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR

    def test_round_trip_preserves_facit_text_and_automatic_values(self) -> None:
        document = _document(
            _gap_fill_item(
                accepted=("katt",),
                automatic=("kat", "ktat", "kattn", "hund"),
                facit_text="Djuret som eftersöks är en katt.",
            )
        )
        (item,) = document.items

        assert item.facit_text == "Djuret som eftersöks är en katt."
        assert item.gaps[0].automatic_values == ("kat", "ktat", "kattn")
        assert parse_native_exam_document(native_exam_document_json_bytes(document)) == document


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
            _gap_fill_item(origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED, accepted=())

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
                answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED),
                review=_review(),
            )

    def test_non_gap_item_must_not_place_gap_segments(self) -> None:
        with pytest.raises(ValidationError, match="only gap_fill"):
            NativeExamItem(
                item_id="item_001",
                sequence=1,
                kind=NativeExamItemKind.FREE_TEXT,
                body=(NativeParagraph(segments=(NativeGapSegment(gap_id="gap_001"),)),),
                answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
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
                answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
                review=_review(),
            )


class TestMatchingInvariants:
    def test_many_to_many_key_with_an_unused_column_validates(self) -> None:
        item = _matching_item(
            pairs=(
                ("left_001", "right_001"),
                ("left_001", "right_002"),
                ("left_002", "right_002"),
                ("left_003", "right_003"),
            ),
            match_right=("right_001", "right_002", "right_003", "right_004"),
            points=4,
        )

        assert [(p.left_id, p.right_id) for p in item.answer_key.match_pairs] == [
            ("left_001", "right_001"),
            ("left_001", "right_002"),
            ("left_002", "right_002"),
            ("left_003", "right_003"),
        ]
        paired = {p.right_id for p in item.answer_key.match_pairs}
        assert [e.right_id for e in item.match_right if e.right_id not in paired] == ["right_004"]
        assert item.points == 4

    def test_left_entry_without_a_pair_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="pairs every left entry at least once"):
            _matching_item(pairs=(("left_001", "right_001"), ("left_002", "right_002")))

    def test_one_pair_repeated_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="pairs a left and right entry at most once"):
            _matching_item(
                pairs=(
                    ("left_001", "right_001"),
                    ("left_001", "right_001"),
                    ("left_002", "right_002"),
                    ("left_003", "right_003"),
                ),
                points=4,
            )

    def test_points_must_equal_tick_times_pairs(self) -> None:
        with pytest.raises(ValidationError, match="tick_points times the number of pairs"):
            _matching_item(points=2)

        item = _matching_item(tick_points=Decimal("0.5"), points=1.5)

        assert item.tick_points == Decimal("0.5")
        assert item.points == 1.5

    def test_points_are_required_for_a_keyed_grid(self) -> None:
        with pytest.raises(ValidationError, match="tick_points times the number of pairs"):
            _matching_item(points=None)

    def test_two_decimal_tick_round_trips_through_stored_json(self) -> None:
        item = _matching_item(
            pairs=(
                ("left_001", "right_001"),
                ("left_002", "right_002"),
                ("left_003", "right_001"),
            ),
            tick_points=Decimal("0.1"),
            points=0.3,
        )

        restored = parse_native_exam_document(native_exam_document_json_bytes(_document(item)))

        assert restored.items[0].tick_points == Decimal("0.1")
        assert restored.items[0].points == 0.3

    def test_tick_points_are_required_on_a_matching_item(self) -> None:
        with pytest.raises(ValidationError, match="need a tick_points value"):
            _matching_item(tick_points=None)

    @pytest.mark.parametrize("tick_points", [Decimal("0"), Decimal("-1"), Decimal("1.234")])
    def test_tick_points_must_be_positive_with_at_most_two_decimals(
        self, tick_points: Decimal
    ) -> None:
        with pytest.raises(ValidationError):
            _matching_item(tick_points=tick_points)

    def test_non_matching_items_carry_no_tick_points(self) -> None:
        with pytest.raises(ValidationError, match="only matching items carry tick_points"):
            NativeExamItem.model_validate({**_free_text_item().model_dump(), "tick_points": "1"})

    def test_unkeyed_grid_carries_a_tick_value_but_no_points(self) -> None:
        item = _matching_item(
            pairs=(),
            origin=NativeAnswerKeyOrigin.ABSENT,
            points=None,
        )

        assert item.tick_points == Decimal("1")
        assert item.points is None

    def test_unkeyed_grid_rejects_a_points_value(self) -> None:
        with pytest.raises(ValidationError, match="tick_points times the number of pairs"):
            _matching_item(pairs=(), origin=NativeAnswerKeyOrigin.ABSENT, points=3)


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


class TestExportBlockers:
    def test_clean_document_has_no_blockers(self) -> None:
        assert native_export_blockers(_document(_gap_fill_item())) == ()

    def test_a_converted_item_that_needs_review_with_points_and_key_does_not_block(
        self,
    ) -> None:
        item = _gap_fill_item().model_copy(
            update={
                "review": _review(
                    state=NativeItemReviewState.REVIEW_REQUIRED,
                    parse_origin=NativeParseOrigin.LLM_PARSED,
                    confidence=0.4,
                )
            }
        )
        assert item.points is not None
        assert native_export_blockers(_document(item)) == ()

    def test_an_unbuilt_question_blocks_until_marked_reviewed(self) -> None:
        unbuilt = _gap_fill_item().model_copy(
            update={
                "points": 2,
                "points_estimated": True,
                "review": _review(
                    state=NativeItemReviewState.REVIEW_REQUIRED,
                    parse_origin=NativeParseOrigin.DETERMINISTIC,
                ),
            }
        )
        reasons = [blocker.reason for blocker in native_export_blockers(_document(unbuilt))]
        assert reasons == ["unbuilt_question"]

        review = unbuilt.review.model_copy(update={"state": NativeItemReviewState.REVIEW_COMPLETE})
        reviewed = unbuilt.model_copy(update={"review": review})
        assert native_export_blockers(_document(reviewed)) == ()

    def test_estimated_points_require_points(self) -> None:
        with pytest.raises(ValidationError, match="estimated points require points"):
            NativeExamItem.model_validate(
                {**_gap_fill_item().model_dump(), "points": None, "points_estimated": True}
            )

    def test_machine_proposed_key_blocks_export(self) -> None:
        item = _single_choice_item(origin=NativeAnswerKeyOrigin.MACHINE_PROPOSED)
        reasons = {blocker.reason for blocker in native_export_blockers(_document(item))}
        assert "machine_proposed_key_unreviewed" in reasons

    def test_ai_interpreted_key_is_trusted_and_does_not_block_export(self) -> None:
        item = _single_choice_item(origin=NativeAnswerKeyOrigin.AI_INTERPRETED)

        assert item_has_trusted_key(item)
        assert native_export_blockers(_document(item)) == ()

    def test_machine_proposed_key_is_not_trusted(self) -> None:
        item = _single_choice_item(origin=NativeAnswerKeyOrigin.MACHINE_PROPOSED)

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
            item = _gap_fill_item(origin=NativeAnswerKeyOrigin.ABSENT, accepted=())
        else:
            item = _single_choice_item(origin=NativeAnswerKeyOrigin.ABSENT, correct=())
            item = NativeExamItem.model_validate({**item.model_dump(), "kind": kind})

        blockers = native_export_blockers(_document(item))

        assert [(blocker.item_id, blocker.reason) for blocker in blockers] == [
            ("item_001", "missing_answer_key")
        ]

    def test_free_text_item_needs_no_answer_key(self) -> None:
        assert native_export_blockers(_document(_free_text_item())) == ()

    def test_missing_points_blocks_export(self) -> None:
        item = _free_text_item().model_copy(update={"points": None})
        reasons = {blocker.reason for blocker in native_export_blockers(_document(item))}
        assert "missing_points" in reasons


class TestAutomaticValues:
    def test_automatic_values_keep_only_bounded_disjoint_spellings(self) -> None:
        gap = NativeGap(
            gap_id="gap_001",
            accepted_values=("mobiltelefon",),
            automatic_values=(
                "mobiltelefone",
                "mobiltelefons",
                "mobil",
                "mobiltelefon",
                "Mobiltelefone",
                "mobiltelefonx",
                "mobiltelefony",
                "mobiltelefonz",
            ),
        )

        assert gap.automatic_values == ("mobiltelefone", "mobiltelefons", "mobiltelefonx")

    def test_automatic_values_without_an_accepted_value_are_dropped(self) -> None:
        gap = NativeGap(gap_id="gap_001", automatic_values=("NE",))

        assert gap.automatic_values == ()

    def test_automatic_values_equal_to_an_accepted_value_case_folded_are_dropped(self) -> None:
        gap = NativeGap(
            gap_id="gap_001",
            accepted_values=("NF",),
            automatic_values=("nf", "NE"),
        )

        assert gap.automatic_values == ("NE",)

    def test_a_changed_accepted_value_drops_its_orphaned_automatic_values(self) -> None:
        item = _gap_fill_item(accepted=("katt",), automatic=("kat", "ktat", "kattn"))
        edited = NativeExamItem.model_validate(
            {
                **item.model_dump(),
                "gaps": [
                    {
                        **item.gaps[0].model_dump(),
                        "accepted_values": ["hund"],
                    }
                ],
            }
        )

        assert edited.gaps[0].automatic_values == ()

    def test_absent_key_admits_no_automatic_values_without_accepted_values(self) -> None:
        item = _gap_fill_item(
            origin=NativeAnswerKeyOrigin.ABSENT,
            accepted=(),
            automatic=("NE",),
        )

        assert item.gaps[0].automatic_values == ()


class TestApiOutputSchema:
    def test_output_schemas_require_the_new_frontend_fields(self) -> None:
        gap_schema = NativeGap.model_json_schema(mode="serialization")
        item_schema = NativeExamItem.model_json_schema(mode="serialization")

        assert "automatic_values" in gap_schema.get("required", ())
        assert "facit_text" in item_schema.get("required", ())
        assert "tick_points" in item_schema.get("required", ())

    def test_input_schemas_keep_the_defaults_optional(self) -> None:
        gap_schema = NativeGap.model_json_schema(mode="validation")
        item_schema = NativeExamItem.model_json_schema(mode="validation")

        assert "automatic_values" not in gap_schema.get("required", ())
        assert "facit_text" not in item_schema.get("required", ())
        assert "tick_points" not in item_schema.get("required", ())
