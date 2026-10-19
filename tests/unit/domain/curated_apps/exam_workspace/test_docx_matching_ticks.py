"""DOCX build of category-sorting grids: many-to-many keys and one uniform tick value.

Task TASK-SKRIPT-39-09-03 T5, story terms Q9-Q11 and plan R12: the produced contract
accepts several ticks per row, and the native build turns the answer key's printed points
into one tick value, floored to 2 decimals, with the derived total and an estimate flag.
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedItem,
    ProducedMatchPair,
    ProducedParagraph,
    ProducedSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text

pytestmark = pytest.mark.unit

_LEFT = ("Katt", "Bil", "Äpple")
_RIGHT = ("Djur", "Fordon", "Frukt")
_ONE_TO_ONE = (("Katt", "Djur"), ("Bil", "Fordon"), ("Äpple", "Frukt"))


def _grid(
    *,
    points: int | None = 6,
    left: tuple[str, ...] = _LEFT,
    right: tuple[str, ...] = _RIGHT,
    pairs: tuple[tuple[str, str], ...] = _ONE_TO_ONE,
) -> ProducedItem:
    keyed = bool(pairs)
    return ProducedItem(
        source_anchors=("body:0001",),
        outcome="converted",
        review_reason=None,
        kind=NativeExamItemKind.MATCHING,
        key_source="copied" if keyed else None,
        facit_text="Facit: Katt–Djur, Bil–Fordon, Äpple–Frukt" if keyed else None,
        body=(
            ProducedParagraph(
                segments=(
                    ProducedSegment(
                        kind="text",
                        text="Kategorisera.",
                        accepted_values=(),
                    ),
                )
            ),
        ),
        points=points,
        choices=(),
        match_left=left,
        match_right=right,
        match_pairs=tuple(ProducedMatchPair(left=a, right=b) for a, b in pairs),
    )


def _number(value: Decimal | int | float | None) -> float:
    assert value is not None
    return float(value)


def test_exact_division_gives_every_tick_the_printed_points_over_the_ticks():
    item = aligned_native_item(_grid(points=6), language="sv", foreign_chunks=()).item

    assert item.kind is NativeExamItemKind.MATCHING
    assert _number(item.tick_points) == 2.0
    assert _number(item.points) == 6.0
    assert item.points_estimated is False
    assert len(item.answer_key.match_pairs) == 3


def test_inexact_division_floors_the_tick_to_two_decimals_and_marks_points_estimated():
    item = aligned_native_item(_grid(points=10), language="sv", foreign_chunks=()).item

    assert _number(item.tick_points) == 3.33
    assert _number(item.points) == pytest.approx(9.99)
    assert item.points_estimated is True


def test_half_point_ticks_are_exact():
    item = aligned_native_item(
        _grid(points=1, left=_LEFT[:2], right=_RIGHT[:2], pairs=_ONE_TO_ONE[:2]),
        language="sv",
        foreign_chunks=(),
    ).item

    assert _number(item.tick_points) == 0.5
    assert _number(item.points) == 1.0
    assert item.points_estimated is False


def test_missing_answer_key_points_use_the_default_tick_one_and_estimate_the_points():
    item = aligned_native_item(_grid(points=None), language="sv", foreign_chunks=()).item

    assert _number(item.tick_points) == 1.0
    assert _number(item.points) == 3.0
    assert item.points_estimated is True


def test_many_to_many_columns_and_an_unused_column_build_one_native_pair_per_tick():
    item = aligned_native_item(
        _grid(
            points=6,
            left=("Katt", "Bil", "Äpple"),
            right=("Djur", "Fordon"),
            pairs=(("Katt", "Djur"), ("Bil", "Djur"), ("Äpple", "Fordon")),
        ),
        language="sv",
        foreign_chunks=(),
    ).item

    assert item.answer_key.origin is NativeAnswerKeyOrigin.SOURCE_PROVIDED
    assert [(p.left_id, p.right_id) for p in item.answer_key.match_pairs] == [
        ("left_001", "right_001"),
        ("left_002", "right_001"),
        ("left_003", "right_002"),
    ]
    assert [e.right_id for e in item.match_right] == ["right_001", "right_002"]
    assert _number(item.tick_points) == 2.0
    assert _number(item.points) == 6.0


def test_one_row_may_tick_two_categories_and_a_category_may_stay_unused():
    item = aligned_native_item(
        _grid(
            points=4,
            left=("Katt", "Bil"),
            right=("Djur", "Fordon", "Frukt"),
            pairs=(("Katt", "Djur"), ("Katt", "Fordon"), ("Bil", "Djur")),
        ),
        language="sv",
        foreign_chunks=(),
    ).item

    assert [(p.left_id, p.right_id) for p in item.answer_key.match_pairs] == [
        ("left_001", "right_001"),
        ("left_001", "right_002"),
        ("left_002", "right_001"),
    ]
    assert [body_plain_text(e.body) for e in item.match_right] == ["Djur", "Fordon", "Frukt"]
    assert _number(item.tick_points) == 1.33
    assert _number(item.points) == pytest.approx(3.99)
    assert item.points_estimated is True


def test_a_duplicate_pair_is_rejected_by_the_produced_contract():
    pairs = (("Katt", "Djur"), ("Katt", "Djur"), ("Bil", "Fordon"), ("Äpple", "Frukt"))

    with pytest.raises(ValidationError, match="states each pair at most once"):
        _grid(pairs=pairs)


def test_a_left_entry_without_any_tick_is_rejected_by_the_produced_contract():
    pairs = (("Katt", "Djur"), ("Bil", "Fordon"))

    with pytest.raises(ValidationError, match="names every match_left entry at least once"):
        _grid(pairs=pairs)


def test_unkeyed_grid_keeps_the_default_tick_and_drops_printed_points():
    item = aligned_native_item(_grid(points=6, pairs=()), language="sv", foreign_chunks=()).item

    assert item.answer_key.origin is NativeAnswerKeyOrigin.ABSENT
    assert item.tick_points == Decimal(1)
    assert item.points is None
    assert item.points_estimated is False


def test_a_grid_whose_floor_cannot_be_positive_is_refused_not_rounded_up():
    left = tuple(f"Rad {number}" for number in range(1, 102))
    pairs = tuple((entry, "Kategori") for entry in left)

    with pytest.raises(ValueError, match="cannot give a positive tick value"):
        aligned_native_item(
            _grid(points=1, left=left, right=("Kategori",), pairs=pairs),
            language="sv",
            foreign_chunks=(),
        ).item
