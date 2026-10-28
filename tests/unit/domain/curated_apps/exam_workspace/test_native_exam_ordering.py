"""Ordering questions: the saved print order and the item's shape (TASK-SKRIPT-39-06-08)."""

import random
from collections.abc import MutableSequence
from itertools import permutations

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_ordering import (
    draw_print_order,
    validate_print_order,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import NativeAnswerKey
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    IMPORTABLE_ITEM_KINDS,
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
    make_ordering_item,
    make_single_choice_item,
)


class _IdentityShuffle(random.Random):
    """A random source whose shuffle always leaves the key order, the D6 worst case."""

    def shuffle(self, x: MutableSequence[object]) -> None:
        return None


@pytest.mark.parametrize("count", range(2, 7))
def test_a_draw_never_equals_the_key_order(count: int) -> None:
    steps = tuple(f"choice_{index:03d}" for index in range(1, count + 1))
    seen: set[tuple[str, ...]] = set()
    for seed in range(400):
        order = draw_print_order(steps, random.Random(seed))
        assert order != steps
        assert sorted(order) == sorted(steps)
        seen.add(order)
    # Every non-key permutation is reachable for small step counts.
    if count <= 4:
        assert seen == set(permutations(steps)) - {steps}


@pytest.mark.parametrize("count", range(2, 7))
def test_a_shuffle_that_returns_the_key_order_is_still_moved(count: int) -> None:
    steps = tuple(f"choice_{index:03d}" for index in range(1, count + 1))
    for seed in range(20):
        rng = _IdentityShuffle(seed)
        order = draw_print_order(steps, rng)
        assert order != steps
        assert sorted(order) == sorted(steps)


def test_one_step_prints_as_itself() -> None:
    assert draw_print_order(("choice_001",), random.Random(1)) == ("choice_001",)


@pytest.mark.parametrize(
    ("steps", "print_order"),
    [
        (("choice_001", "choice_002"), ("choice_001", "choice_002")),
        (("choice_001", "choice_002"), ("choice_002",)),
        (("choice_001", "choice_002"), ("choice_002", "choice_001", "choice_001")),
        (("choice_001", "choice_002"), ("choice_002", "choice_003")),
    ],
)
def test_a_print_order_that_is_the_key_or_not_a_permutation_is_refused(
    steps: tuple[str, ...], print_order: tuple[str, ...]
) -> None:
    with pytest.raises(ValueError):
        validate_print_order(steps, print_order)


def test_an_ordering_item_saves_with_its_print_order() -> None:
    item = make_ordering_item(print_order=("choice_003", "choice_001", "choice_004", "choice_002"))
    assert item.print_order == ("choice_003", "choice_001", "choice_004", "choice_002")
    assert item.answer_key.correct_choice_ids == ()


def test_an_ordering_item_printed_in_key_order_is_refused() -> None:
    with pytest.raises(ValidationError, match="differ from the answer-key order"):
        make_ordering_item(print_order=("choice_001", "choice_002", "choice_003", "choice_004"))


def test_one_step_saves_so_the_export_blocker_can_name_it() -> None:
    item = make_ordering_item(steps=("Tes",), print_order=("choice_001",))
    assert len(item.choices) == 1


def test_an_ordering_item_without_steps_is_refused() -> None:
    payload = make_ordering_item().model_dump()
    payload.update(choices=(), print_order=())
    with pytest.raises(ValidationError, match="at least one step"):
        type(make_ordering_item()).model_validate(payload)


@pytest.mark.parametrize(
    "key",
    [
        NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT),
        NativeAnswerKey(origin=NativeAnswerKeyOrigin.MACHINE_PROPOSED),
        NativeAnswerKey(
            origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED, correct_choice_ids=("choice_001",)
        ),
    ],
)
def test_an_ordering_key_is_only_the_teachers_list_order(key: NativeAnswerKey) -> None:
    payload = make_ordering_item().model_dump()
    payload["answer_key"] = key
    with pytest.raises(ValidationError):
        type(make_ordering_item()).model_validate(payload)


def test_only_ordering_items_carry_a_print_order() -> None:
    payload = make_single_choice_item().model_dump()
    payload["print_order"] = ("choice_002", "choice_001")
    with pytest.raises(ValidationError, match="only ordering items carry a print order"):
        type(make_single_choice_item()).model_validate(payload)


def test_an_ordering_item_inside_a_parent_is_accepted_at_one_point() -> None:
    document = make_document(
        make_free_text_item(item_id="item_001", sequence=1),
        make_ordering_item(item_id="item_002", sequence=2),
    )
    payload = document.model_dump()
    payload["parents"] = [
        {
            "parent_id": "parent_001",
            "place": 0,
            "instruction": [
                {"heading_level": None, "segments": [{"kind": "text", "text": "Läs.", "marks": []}]}
            ],
            "item_ids": ["item_001", "item_002"],
        }
    ]

    saved = NativeExamDocument.model_validate(payload)

    assert saved.parent_of("item_002") is not None
    assert saved.item_by_id("item_002").points == 1

    payload["items"][1]["points"] = 3
    with pytest.raises(ValidationError, match="worth exactly 1 point"):
        NativeExamDocument.model_validate(payload)


def test_imports_never_produce_ordering() -> None:
    assert NativeExamItemKind.ORDERING not in IMPORTABLE_ITEM_KINDS
    assert IMPORTABLE_ITEM_KINDS == frozenset(NativeExamItemKind) - {NativeExamItemKind.ORDERING}
