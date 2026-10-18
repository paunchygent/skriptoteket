"""Adversarial grouping, moving and empty-part commands over recorded DOCX conversion items."""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_json import (
    native_exam_document_json_bytes,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import NativeExamParent
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent_commands import (
    add_child,
    create_empty_part,
    create_parent,
    delete_child,
    delete_parent,
    group_items,
    move_item,
    reorder_children,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
    make_ordering_item,
    plain_body,
)
from tests.unit.domain.curated_apps.exam_workspace.parent_commands_test_support import (
    _check_structure,
    _exam,
    _saved_exam,
)
from tests.unit.domain.curated_apps.exam_workspace.recorded_native_exam_support import (
    parent_over,
    recorded_document,
    recorded_items,
)


def _childless(parent_id: str, instruction: str, place: int) -> NativeExamParent:
    return NativeExamParent(parent_id=parent_id, place=place, instruction=plain_body(instruction))


def _with_parts(document: NativeExamDocument, *parts: NativeExamParent) -> NativeExamDocument:
    parents = sorted(
        (*document.parents, *parts), key=lambda parent: (parent.place, bool(parent.item_ids))
    )
    return NativeExamDocument.model_validate({**document.model_dump(), "parents": parents})


def test_create_parent_counts_a_childless_part_as_a_top_level_position() -> None:
    base = _with_parts(_exam(), _childless("parent_002", "Instruktionsblock", 4))
    template = next(item for item in base.items if item.kind is NativeExamItemKind.GAP_FILL)

    result = create_parent(base, instruction=plain_body("Ny del"), child=template, position=3)

    new_parent = next(
        parent for parent in result.parents if parent.parent_id not in {"parent_001", "parent_002"}
    )
    (child_id,) = new_parent.item_ids
    assert [item.item_id for item in result.items[:6]] == [
        "item_001",
        "item_002",
        "item_003",
        "item_004",
        child_id,
        "item_005",
    ]
    assert new_parent.place == 4
    preserved = next(parent for parent in result.parents if parent.parent_id == "parent_002")
    assert preserved.item_ids == ()
    assert preserved.place == 5, "The inserted question now stands before the block"
    assert result.parents.index(preserved) > result.parents.index(new_parent)
    _check_structure(result)


def test_delete_parent_leaves_children_standalone_at_the_parts_place() -> None:
    base = _with_parts(_saved_exam(), _childless("parent_003", "Instruktionsblock", 4))
    block = next(parent for parent in base.parents if parent.parent_id == "parent_003")

    result = delete_parent(base, parent_id="parent_001")

    assert all(
        result.parent_of(item_id) is None for item_id in ("item_002", "item_003", "item_004")
    )
    assert [
        result.item_by_id(item_id).sequence for item_id in ("item_002", "item_003", "item_004")
    ] == [
        2,
        3,
        4,
    ]
    assert next(parent for parent in result.parents if parent.parent_id == "parent_003") == block
    _check_structure(result)


def test_reorder_children_and_add_child_keep_a_childless_part_at_its_place() -> None:
    base = _with_parts(_exam(), _childless("parent_002", "Instruktionsblock", 5))
    block = next(parent for parent in base.parents if parent.parent_id == "parent_002")
    template = next(item for item in base.items if item.kind is NativeExamItemKind.GAP_FILL)

    reordered = reorder_children(base, parent_id="parent_001", item_ids=("item_003", "item_002"))
    assert next(parent for parent in reordered.parents if parent.parent_id == "parent_002") == block

    added = add_child(reordered, parent_id="parent_001", child=template, position=1)
    preserved = next(parent for parent in added.parents if parent.parent_id == "parent_002")
    assert preserved.item_ids == ()
    assert preserved.place == block.place + 1
    assert preserved.place == added.item_by_id("item_005").sequence
    _check_structure(added)


def _six() -> NativeExamDocument:
    return recorded_document(items=recorded_items()[:6])


def test_group_non_adjacent_questions_takes_the_first_place_and_keeps_the_rest_in_order() -> None:
    base = _six()
    original = native_exam_document_json_bytes(base)

    result, parent_id = group_items(base, item_ids=("item_002", "item_005"))

    assert [item.item_id for item in result.items] == [
        "item_001",
        "item_002",
        "item_005",
        "item_003",
        "item_004",
        "item_006",
    ]
    assert [item.sequence for item in result.items] == [1, 2, 3, 4, 5, 6]
    part = next(parent for parent in result.parents if parent.parent_id == parent_id)
    assert part.item_ids == ("item_002", "item_005")
    assert part.place == 1, "The part takes the place of the earliest marked question (G10)"
    assert part.instruction == (), "A new part starts with an empty instruction (G4)"
    assert [result.item_by_id(item_id).sequence for item_id in part.item_ids] == [2, 3]
    assert native_exam_document_json_bytes(base) == original
    _check_structure(result)


def test_group_one_question_makes_a_part_holding_exactly_that_question() -> None:
    base = _six()

    result, parent_id = group_items(base, item_ids=("item_002",))

    part = next(parent for parent in result.parents if parent.parent_id == parent_id)
    assert part.item_ids == ("item_002",)
    assert part.place == 1
    assert [item.item_id for item in result.items] == [
        "item_001",
        "item_002",
        "item_003",
        "item_004",
        "item_005",
        "item_006",
    ]
    _check_structure(result)


def test_group_refuses_empty_duplicate_and_unknown_items_with_named_reasons() -> None:
    base = _six()

    with pytest.raises(DomainError) as empty:
        group_items(base, item_ids=())
    assert empty.value.code is ErrorCode.VALIDATION_ERROR
    assert empty.value.message == "Markera minst en fråga."
    assert empty.value.details == {"reason": "no_items"}

    with pytest.raises(DomainError) as duplicate:
        group_items(base, item_ids=("item_002", "item_002"))
    assert duplicate.value.details == {"reason": "duplicate_items"}

    with pytest.raises(DomainError) as unknown:
        group_items(base, item_ids=("item_999",))
    assert unknown.value.code is ErrorCode.NOT_FOUND
    assert unknown.value.details == {"item_id": "item_999"}


def test_group_refuses_an_existing_child_and_an_ordering_question() -> None:
    with pytest.raises(DomainError) as child:
        group_items(_exam(), item_ids=("item_002",))
    assert child.value.code is ErrorCode.VALIDATION_ERROR
    assert child.value.message == "Frågan ligger redan i en del. Flytta den med Flytta till…"
    assert child.value.details == {"reason": "item_in_part", "item_id": "item_002"}

    ordering = make_document(
        make_free_text_item(sequence=1, item_id="item_001"),
        make_ordering_item(sequence=2, item_id="item_002"),
    )
    with pytest.raises(DomainError) as ordering_error:
        group_items(ordering, item_ids=("item_002",))
    assert ordering_error.value.details == {
        "reason": "ordering_inside_parent",
        "item_id": "item_002",
    }


def test_move_standalone_into_a_part_lands_last_and_keeps_the_parts_place() -> None:
    base = _exam()

    result = move_item(base, item_id="item_001", target_parent_id="parent_001")

    part = result.parents[0]
    assert part.parent_id == "parent_001"
    assert part.item_ids == ("item_002", "item_003", "item_001")
    assert part.place == 0
    assert [result.item_by_id(item_id).sequence for item_id in part.item_ids] == [1, 2, 3]
    assert result.item_by_id("item_001").sequence == 3
    _check_structure(result)


def test_move_between_parts_lands_last_in_the_target_and_the_source_keeps_its_place() -> None:
    base = recorded_document(
        (parent_over("parent_001", "A", 2, 3), parent_over("parent_002", "B", 5, 6))
    )

    result = move_item(base, item_id="item_002", target_parent_id="parent_002")

    source = next(parent for parent in result.parents if parent.parent_id == "parent_001")
    target = next(parent for parent in result.parents if parent.parent_id == "parent_002")
    assert source.item_ids == ("item_003",)
    assert source.place == 1
    assert target.item_ids == ("item_005", "item_006", "item_002")
    assert result.item_by_id("item_002").sequence == target.place + 3
    _check_structure(result)

    emptied = move_item(result, item_id="item_003", target_parent_id="parent_002")

    source = next(parent for parent in emptied.parents if parent.parent_id == "parent_001")
    target = next(parent for parent in emptied.parents if parent.parent_id == "parent_002")
    assert source.item_ids == (), "A part left with no questions stays (G8)"
    assert source.place == 1
    assert target.item_ids[-1] == "item_003"
    _check_structure(emptied)


def test_move_out_lands_directly_after_the_part_it_left() -> None:
    base = _exam()

    result = move_item(base, item_id="item_002", target_parent_id=None)

    part = result.parents[0]
    assert part.item_ids == ("item_003",)
    assert result.item_by_id("item_002").sequence == part.place + len(part.item_ids) + 1
    assert [item.item_id for item in result.items][:4] == [
        "item_001",
        "item_003",
        "item_002",
        "item_004",
    ]
    _check_structure(result)


def test_move_out_of_a_one_question_part_leaves_a_childless_part_before_the_question() -> None:
    base = recorded_document((parent_over("parent_001", "A", 2),))

    result = move_item(base, item_id="item_002", target_parent_id=None)

    part = result.parents[0]
    assert part.item_ids == ()
    assert part.place == 1
    assert result.item_by_id("item_002").sequence == 2
    _check_structure(result)


def test_move_refuses_unknown_ids_the_same_part_and_ordering_into_a_part() -> None:
    base = _exam()

    with pytest.raises(DomainError) as unknown_part:
        move_item(base, item_id="item_002", target_parent_id="parent_999")
    assert unknown_part.value.code is ErrorCode.NOT_FOUND
    assert unknown_part.value.details == {"parent_id": "parent_999"}

    with pytest.raises(DomainError) as same_part:
        move_item(base, item_id="item_002", target_parent_id="parent_001")
    assert same_part.value.details == {
        "reason": "already_in_part",
        "parent_id": "parent_001",
        "item_id": "item_002",
    }

    with pytest.raises(DomainError) as standalone:
        move_item(base, item_id="item_001", target_parent_id=None)
    assert standalone.value.details == {"reason": "already_standalone", "item_id": "item_001"}

    with pytest.raises(DomainError) as unknown_item:
        move_item(base, item_id="item_999", target_parent_id=None)
    assert unknown_item.value.code is ErrorCode.NOT_FOUND
    assert unknown_item.value.details == {"item_id": "item_999"}

    ordering = _with_parts(
        make_document(
            make_free_text_item(sequence=1, item_id="item_001"),
            make_ordering_item(sequence=2, item_id="item_002"),
        ),
        _childless("parent_001", "Block", 1),
    )
    with pytest.raises(DomainError) as ordering_error:
        move_item(ordering, item_id="item_002", target_parent_id="parent_001")
    assert ordering_error.value.details == {
        "reason": "ordering_inside_parent",
        "item_id": "item_002",
    }


@pytest.mark.parametrize("position", [0, 3, 6])
def test_create_empty_part_inserts_a_childless_instruction_block_at_the_position(
    position: int,
) -> None:
    base = _six()

    result, parent_id = create_empty_part(base, position=position)

    part = next(parent for parent in result.parents if parent.parent_id == parent_id)
    assert part.item_ids == ()
    assert part.instruction == ()
    assert part.place == position
    assert [item.item_id for item in result.items] == [
        "item_001",
        "item_002",
        "item_003",
        "item_004",
        "item_005",
        "item_006",
    ]
    _check_structure(result)


def test_create_empty_part_refuses_a_position_beyond_the_outline() -> None:
    with pytest.raises(DomainError) as error:
        create_empty_part(_six(), position=7)

    assert error.value.code is ErrorCode.VALIDATION_ERROR
    assert error.value.message == "Positionen finns inte."
    assert error.value.details == {"position": 7}


def test_a_childless_part_is_never_lost_by_group_move_empty_or_delete() -> None:
    base = _with_parts(_six(), _childless("parent_001", "Instruktionsblock", 3))

    grouped, new_part_id = group_items(base, item_ids=("item_002", "item_005"))
    assert next(p for p in grouped.parents if p.parent_id == "parent_001").item_ids == ()

    moved = move_item(grouped, item_id="item_006", target_parent_id=new_part_id)
    assert next(p for p in moved.parents if p.parent_id == "parent_001").item_ids == ()

    emptied, _ = create_empty_part(moved, position=0)
    surviving = next(p for p in emptied.parents if p.parent_id == "parent_001")
    assert surviving.item_ids == ()
    assert surviving.place == 5

    deleted = delete_child(emptied, parent_id=new_part_id, item_id="item_002")
    surviving = next(p for p in deleted.parents if p.parent_id == "parent_001")
    assert surviving.item_ids == ()
    assert surviving.place == 4
    target = next(p for p in deleted.parents if p.parent_id == new_part_id)
    assert target.item_ids == ("item_005", "item_006")
    _check_structure(deleted)
