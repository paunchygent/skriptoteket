"""Unit tests for the source-neutral native exam document (ST-SKRIPT-39-04)."""

import json
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_criteria import (
    NativeExamCriterion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_json import (
    native_exam_document_json_bytes,
    parse_native_exam_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_matching import (
    NativeMatchLeft,
    NativeMatchPair,
    NativeMatchRight,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeGap,
    NativeItemReview,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
    make_gap_fill_item,
    make_single_choice_item,
)


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
        document = make_document(
            make_gap_fill_item(sequence=1, item_id="item_001"),
            make_single_choice_item(sequence=2, item_id="item_002"),
            make_free_text_item(sequence=3, item_id="item_003"),
        )
        payload = native_exam_document_json_bytes(document)
        assert parse_native_exam_document(payload) == document

    def test_serialization_is_deterministic(self) -> None:
        document = make_document(make_free_text_item())
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
        assert make_document(make_free_text_item()).schema_version == "native_exam_document_v2"

    def test_saved_v1_payload_has_no_compatibility_reader(self) -> None:
        document = make_document(make_free_text_item())
        payload = json.loads(native_exam_document_json_bytes(document))
        payload["schema_version"] = "native_exam_document_v1"

        with pytest.raises(DomainError) as exc_info:
            parse_native_exam_document(json.dumps(payload).encode("utf-8"))

        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR

    def test_round_trip_preserves_facit_text_and_automatic_values(self) -> None:
        document = make_document(
            make_gap_fill_item(
                accepted=("katt",),
                automatic=("kat", "ktat", "kattn", "hund"),
                facit_text="Djuret som eftersöks är en katt.",
            )
        )
        (item,) = document.items

        assert item.facit_text == "Djuret som eftersöks är en katt."
        assert item.gaps[0].automatic_values == ("kat", "ktat", "kattn")
        assert parse_native_exam_document(native_exam_document_json_bytes(document)) == document

    def test_round_trip_preserves_the_criteria_list(self) -> None:
        item = make_free_text_item().model_copy(
            update={
                "points": 3,
                "criteria": (
                    NativeExamCriterion(text="Ett korrekt exempel.", points=2),
                    NativeExamCriterion(text="En korrekt förklaring.", points=1),
                ),
            }
        )
        document = make_document(item)

        parsed = parse_native_exam_document(native_exam_document_json_bytes(document))

        assert parsed == document
        assert parsed.items[0].criteria[1].text == "En korrekt förklaring."


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
            make_document(
                make_free_text_item(sequence=1, item_id="item_001"),
                make_free_text_item(sequence=3, item_id="item_002"),
            )

    def test_item_ids_must_be_unique(self) -> None:
        with pytest.raises(ValidationError, match="unique"):
            make_document(
                make_free_text_item(sequence=1, item_id="item_001"),
                make_free_text_item(sequence=2, item_id="item_001"),
            )

    def test_docx_import_origin_requires_source_fields(self) -> None:
        with pytest.raises(ValidationError, match="docx_import origin requires"):
            NativeExamDocumentOrigin(kind="docx_import")


class TestApiOutputSchema:
    def test_output_schemas_require_the_new_frontend_fields(self) -> None:
        gap_schema = NativeGap.model_json_schema(mode="serialization")
        item_schema = NativeExamItem.model_json_schema(mode="serialization")

        assert "automatic_values" in gap_schema.get("required", ())
        assert "facit_text" in item_schema.get("required", ())
        assert "tick_points" in item_schema.get("required", ())
        assert "criteria" in item_schema.get("required", ())

    def test_input_schemas_keep_the_defaults_optional(self) -> None:
        gap_schema = NativeGap.model_json_schema(mode="validation")
        item_schema = NativeExamItem.model_json_schema(mode="validation")

        assert "automatic_values" not in gap_schema.get("required", ())
        assert "facit_text" not in item_schema.get("required", ())
        assert "tick_points" not in item_schema.get("required", ())
        assert "criteria" not in item_schema.get("required", ())
