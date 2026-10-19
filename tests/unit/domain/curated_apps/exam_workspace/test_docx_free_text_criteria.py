"""DOCX conversion of a free_text answer key into the criteria list (Q12, R14)."""

import pytest
from pydantic import JsonValue, ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedCriterion,
    ProducedItem,
    ProducedParagraph,
    ProducedSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_item import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_schema import docx_build_output_spec
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_criteria import (
    NativeExamCriterion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)

pytestmark = pytest.mark.unit


def _object(node: JsonValue) -> dict[str, JsonValue]:
    assert isinstance(node, dict)
    return node


def _produced(
    *,
    points: int | float | None,
    criteria: tuple[ProducedCriterion, ...] = (),
    kind: NativeExamItemKind = NativeExamItemKind.FREE_TEXT,
) -> ProducedItem:
    return ProducedItem(
        source_anchors=("body:0001",),
        outcome="converted",
        review_reason=None,
        kind=kind,
        printed_label=None,
        key_source=None,
        facit_text=None,
        body=(
            ProducedParagraph(
                segments=(ProducedSegment(kind="text", text="Resonera.", accepted_values=()),)
            ),
        ),
        points=points,
        choices=(),
        match_left=(),
        match_right=(),
        match_pairs=(),
        criteria=criteria,
    )


def test_stated_criteria_keep_their_points_and_the_item_points_are_their_sum() -> None:
    item = aligned_native_item(
        _produced(
            points=3,
            criteria=(
                ProducedCriterion(text="Ett exempel.", points=2),
                ProducedCriterion(text="En term.", points=1),
            ),
        ),
        language="sv",
        foreign_chunks=(),
    ).item

    assert item.criteria == (
        NativeExamCriterion(text="Ett exempel.", points=2),
        NativeExamCriterion(text="En term.", points=1),
    )
    assert item.points == 3
    assert item.points_estimated is False


def test_stated_criteria_without_printed_points_take_their_sum() -> None:
    item = aligned_native_item(
        _produced(
            points=None,
            criteria=(
                ProducedCriterion(text="Ett exempel.", points=2),
                ProducedCriterion(text="En term.", points=1),
            ),
        ),
        language="sv",
        foreign_chunks=(),
    ).item

    assert item.points == 3
    assert item.points_estimated is False


def test_guide_without_breakdown_becomes_one_estimated_criterion_at_the_item_points() -> None:
    item = aligned_native_item(
        _produced(points=4, criteria=(ProducedCriterion(text="Bedöm helheten."),)),
        language="sv",
        foreign_chunks=(),
    ).item

    assert item.criteria == (NativeExamCriterion(text="Bedöm helheten.", points=4),)
    assert item.points == 4
    assert item.points_estimated is True


def test_guide_without_breakdown_or_points_becomes_one_estimated_point() -> None:
    item = aligned_native_item(
        _produced(points=None, criteria=(ProducedCriterion(text="Bedöm helheten."),)),
        language="sv",
        foreign_chunks=(),
    ).item

    assert item.criteria == (NativeExamCriterion(text="Bedöm helheten.", points=1),)
    assert item.points == 1
    assert item.points_estimated is True


def test_free_text_without_criteria_keeps_its_printed_points() -> None:
    item = aligned_native_item(_produced(points=8), language="sv", foreign_chunks=()).item

    assert item.criteria == ()
    assert item.points == 8
    assert item.points_estimated is False


def test_fractional_item_points_route_to_review() -> None:
    with pytest.raises(ValueError, match="points are not whole"):
        aligned_native_item(
            _produced(points=2.5, criteria=(ProducedCriterion(text="Bedöm helheten."),)),
            language="sv",
            foreign_chunks=(),
        ).item

    with pytest.raises(ValueError, match="criteria sum does not match"):
        aligned_native_item(
            _produced(
                points=2.5,
                criteria=(
                    ProducedCriterion(text="Ett exempel.", points=2),
                    ProducedCriterion(text="En term.", points=1),
                ),
            ),
            language="sv",
            foreign_chunks=(),
        ).item


def test_fractional_free_text_points_without_criteria_route_to_review() -> None:
    with pytest.raises(ValueError, match="points are not whole"):
        aligned_native_item(_produced(points=2.5), language="sv", foreign_chunks=()).item


def test_fractional_criterion_points_route_to_review() -> None:
    with pytest.raises(ValueError, match="criterion points are not whole"):
        aligned_native_item(
            _produced(
                points=3,
                criteria=(
                    ProducedCriterion(text="Ett exempel.", points=2.5),
                    ProducedCriterion(text="En term.", points=0.5),
                ),
            ),
            language="sv",
            foreign_chunks=(),
        ).item


def test_a_criteria_sum_that_differs_from_the_printed_points_routes_to_review() -> None:
    with pytest.raises(ValueError, match="criteria sum does not match"):
        aligned_native_item(
            _produced(
                points=4,
                criteria=(
                    ProducedCriterion(text="Ett exempel.", points=2),
                    ProducedCriterion(text="En term.", points=1),
                ),
            ),
            language="sv",
            foreign_chunks=(),
        ).item


def test_criteria_below_one_point_route_to_review() -> None:
    with pytest.raises(ValueError, match="criterion points are not whole"):
        aligned_native_item(
            _produced(points=1, criteria=(ProducedCriterion(text="Ett exempel.", points=0),)),
            language="sv",
            foreign_chunks=(),
        ).item


def test_the_produced_schema_carries_criteria_only_for_free_text() -> None:
    with pytest.raises(ValidationError, match="only free_text items carry criteria"):
        _produced(
            points=1,
            kind=NativeExamItemKind.SINGLE_CHOICE,
            criteria=(ProducedCriterion(text="Ett exempel.", points=1),),
        )


def test_a_guide_without_points_is_exactly_one_criterion() -> None:
    with pytest.raises(ValidationError, match="without per-criterion points is one criterion"):
        _produced(
            points=3,
            criteria=(
                ProducedCriterion(text="Bedöm helheten."),
                ProducedCriterion(text="Ett exempel.", points=2),
            ),
        )


def test_the_provider_schema_offers_criteria_and_no_marking_guide() -> None:
    spec = _object(
        docx_build_output_spec(
            anchors=["body:0001"], kinds=[NativeExamItemKind.FREE_TEXT]
        ).json_schema
    )
    definitions = _object(spec["$defs"])
    item_fields = _object(_object(definitions["ProducedItem"])["properties"])
    assert "criteria" in item_fields
    assert "marking_guide" not in item_fields
    criterion_properties = _object(_object(definitions["ProducedCriterion"])["properties"])
    assert set(criterion_properties) == {"text", "points"}
