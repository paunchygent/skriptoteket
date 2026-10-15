"""Native matching items: grid invariants, tick/point scoring and stored-JSON serialization."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_json import (
    native_exam_document_json_bytes,
    parse_native_exam_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    native_export_blockers,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
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
    make_document,
    make_free_text_item,
)
from tests.unit.domain.curated_apps.exam_workspace.native_matching_test_support import (
    keyed_answer,
    matching_item,
    single_item_document,
    valid_item,
    with_distractor,
    with_update,
)


def test_valid_matching_item_validates_with_a_pair_per_entry() -> None:
    item = valid_item()

    assert item.kind is NativeExamItemKind.MATCHING
    assert len(item.match_left) == 3
    assert len(item.match_right) == 3
    assert item.answer_key.origin is NativeAnswerKeyOrigin.SOURCE_PROVIDED
    assert not item.choices
    assert not item.gaps
    assert native_export_blockers(single_item_document(item)) == ()


def test_right_entry_used_twice_is_accepted_even_with_a_distractor_to_spare() -> None:
    item = with_distractor(valid_item())
    pairs = item.answer_key.match_pairs
    reused = (pairs[0], pairs[1].model_copy(update={"right_id": pairs[0].right_id}), pairs[2])

    widened = with_update(
        item, answer_key=item.answer_key.model_copy(update={"match_pairs": reused})
    )

    assert [(p.left_id, p.right_id) for p in widened.answer_key.match_pairs] == [
        (pairs[0].left_id, pairs[0].right_id),
        (pairs[1].left_id, pairs[0].right_id),
        (pairs[2].left_id, pairs[2].right_id),
    ]
    assert native_export_blockers(single_item_document(widened)) == ()


def test_right_entry_without_a_pair_is_a_distractor_and_the_item_validates() -> None:
    item = with_distractor(valid_item())

    assert len(item.match_right) == len(item.match_left) + 1
    paired = {pair.right_id for pair in item.answer_key.match_pairs}
    assert [e.right_id for e in item.match_right if e.right_id not in paired] == ["right_004"]
    assert native_export_blockers(single_item_document(item)) == ()


def test_left_entry_without_a_pair_is_rejected() -> None:
    item = valid_item()
    pairs = item.answer_key.match_pairs[:-1]

    with pytest.raises(ValidationError, match="pairs every left entry at least once"):
        with_update(item, answer_key=item.answer_key.model_copy(update={"match_pairs": pairs}))


def test_left_entry_paired_to_two_rights_is_a_valid_grid() -> None:
    item = valid_item()
    first, second, third = item.answer_key.match_pairs
    doubled = (first, first.model_copy(update={"right_id": second.right_id}), second, third)
    tick_points = item.tick_points
    assert tick_points is not None

    widened = with_update(
        item,
        points=tick_points * 4,
        answer_key=item.answer_key.model_copy(update={"match_pairs": doubled}),
    )

    assert [p.right_id for p in widened.answer_key.match_pairs if p.left_id == first.left_id] == [
        first.right_id,
        second.right_id,
    ]


def test_one_pair_repeated_is_rejected() -> None:
    item = valid_item()
    first, second, third = item.answer_key.match_pairs
    repeated = (first, first, second, third)

    with pytest.raises(ValidationError, match="pairs a left and right entry at most once"):
        with_update(item, answer_key=item.answer_key.model_copy(update={"match_pairs": repeated}))


def test_valid_matching_item_derives_points_from_its_tick_value() -> None:
    item = valid_item()

    assert item.tick_points == Decimal(1)
    assert item.points == len(item.answer_key.match_pairs)


def test_matching_points_must_equal_tick_times_ticks() -> None:
    item = valid_item()
    assert item.points is not None

    with pytest.raises(ValidationError, match="tick_points times the number of pairs"):
        with_update(item, points=item.points + 1)

    fractional = with_update(item, tick_points=Decimal("0.5"), points=1.5)

    assert fractional.tick_points == Decimal("0.5")
    assert fractional.points == 1.5


def test_matching_item_requires_a_tick_value() -> None:
    item = valid_item()

    with pytest.raises(ValidationError, match="need a tick_points value"):
        with_update(item, tick_points=None)


@pytest.mark.parametrize(
    "undeclared",
    [("left_009", "right_001"), ("left_001", "right_009")],
    ids=["left", "right"],
)
def test_pair_naming_an_undeclared_entry_is_rejected(undeclared: tuple[str, str]) -> None:
    item = valid_item()
    key = keyed_answer(undeclared, ("left_002", "right_002"), ("left_003", "right_003"))

    with pytest.raises(ValidationError, match="refer to declared entries"):
        with_update(item, answer_key=key)


def test_pairs_on_a_single_choice_item_are_rejected() -> None:
    item = valid_item()
    choices = (
        NativeChoice(choice_id="choice_001", body=item.match_right[0].body),
        NativeChoice(choice_id="choice_002", body=item.match_right[1].body),
    )
    key = keyed_answer(("left_001", "right_001")).model_copy(
        update={"correct_choice_ids": ("choice_001",)}
    )

    with pytest.raises(ValidationError, match="only matching items key match pairs"):
        with_update(
            item,
            kind=NativeExamItemKind.SINGLE_CHOICE,
            match_left=(),
            match_right=(),
            choices=choices,
            answer_key=key,
        )


def test_pairs_on_a_free_text_item_are_rejected() -> None:
    item = valid_item()
    key = keyed_answer(("left_001", "right_001")).model_copy(
        update={"origin": NativeAnswerKeyOrigin.NOT_APPLICABLE}
    )

    with pytest.raises(ValidationError, match="free_text items carry no answer-key data"):
        with_update(
            item,
            kind=NativeExamItemKind.FREE_TEXT,
            match_left=(),
            match_right=(),
            answer_key=key,
        )


def test_match_lists_on_a_non_matching_kind_are_rejected() -> None:
    item = valid_item()
    key = NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE)

    with pytest.raises(ValidationError, match="only matching items carry match lists"):
        with_update(item, kind=NativeExamItemKind.FREE_TEXT, answer_key=key)


def test_choices_on_a_matching_item_are_rejected() -> None:
    item = valid_item()
    choices = (
        NativeChoice(choice_id="choice_001", body=item.match_right[0].body),
        NativeChoice(choice_id="choice_002", body=item.match_right[1].body),
    )

    with pytest.raises(ValidationError, match="must not declare choices or gaps"):
        with_update(item, choices=choices)


def test_gaps_on_a_matching_item_are_rejected() -> None:
    item = valid_item()

    with pytest.raises(ValidationError, match="must not declare choices or gaps"):
        with_update(item, gaps=(NativeGap(gap_id="gap_001", accepted_values=("x",)),))


def test_single_right_entry_is_rejected_even_when_every_left_entry_is_paired() -> None:
    item = valid_item()
    key = keyed_answer(*(((p.left_id, "right_001")) for p in item.answer_key.match_pairs))

    with pytest.raises(ValidationError, match="at least two right entries"):
        with_update(item, match_right=item.match_right[:1], answer_key=key)


def test_matching_item_without_left_entries_is_rejected() -> None:
    item = valid_item()

    with pytest.raises(ValidationError, match="need left entries"):
        with_update(
            item,
            match_left=(),
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT),
        )


@pytest.mark.parametrize(
    ("origin", "message"),
    [
        (NativeAnswerKeyOrigin.ABSENT, "absent answer key must not carry key data"),
        (NativeAnswerKeyOrigin.NOT_APPLICABLE, "keyed item kinds cannot use not_applicable"),
    ],
)
def test_matching_key_origin_must_agree_with_its_pairs(
    origin: NativeAnswerKeyOrigin, message: str
) -> None:
    item = valid_item()

    with pytest.raises(ValidationError, match=message):
        with_update(item, answer_key=item.answer_key.model_copy(update={"origin": origin}))


def test_duplicate_entry_ids_are_rejected() -> None:
    item = valid_item()
    doubled = (item.match_left[0], item.match_left[0], item.match_left[2])

    with pytest.raises(ValidationError, match="match entry ids must be unique"):
        with_update(item, match_left=doubled)


# --- tick/point scoring and stored JSON from the native document suite -------------------


def test_many_to_many_key_with_an_unused_column_validates() -> None:
    item = matching_item(
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


def test_points_are_required_for_a_keyed_grid() -> None:
    with pytest.raises(ValidationError, match="tick_points times the number of pairs"):
        matching_item(points=None)


def test_two_decimal_tick_round_trips_through_stored_json() -> None:
    item = matching_item(
        pairs=(
            ("left_001", "right_001"),
            ("left_002", "right_002"),
            ("left_003", "right_001"),
        ),
        tick_points=Decimal("0.1"),
        points=0.3,
    )

    restored = parse_native_exam_document(native_exam_document_json_bytes(make_document(item)))

    assert restored.items[0].tick_points == Decimal("0.1")
    assert restored.items[0].points == 0.3


@pytest.mark.parametrize("tick_points", [Decimal("0"), Decimal("-1"), Decimal("1.234")])
def test_tick_points_must_be_positive_with_at_most_two_decimals(tick_points: Decimal) -> None:
    with pytest.raises(ValidationError):
        matching_item(tick_points=tick_points)


def test_non_matching_items_carry_no_tick_points() -> None:
    with pytest.raises(ValidationError, match="only matching items carry tick_points"):
        NativeExamItem.model_validate({**make_free_text_item().model_dump(), "tick_points": "1"})


def test_unkeyed_grid_carries_a_tick_value_but_no_points() -> None:
    item = matching_item(pairs=(), origin=NativeAnswerKeyOrigin.ABSENT, points=None)

    assert item.tick_points == Decimal("1")
    assert item.points is None


def test_unkeyed_grid_rejects_a_points_value() -> None:
    with pytest.raises(ValidationError, match="tick_points times the number of pairs"):
        matching_item(pairs=(), origin=NativeAnswerKeyOrigin.ABSENT, points=3)
