"""The insert rule the conversion merge shares with its client twin (R1)."""

from __future__ import annotations

from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_merge_parents import (
    merged_members,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_outline import (
    MemberBlock,
    MemberItem,
    OutlineMember,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_conversion_support import (
    body,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
)


def _part(parent_id: str, place: int, *child_ids: str) -> NativeExamParent:
    return NativeExamParent(
        parent_id=parent_id,
        place=place,
        instruction=body("Delinstruktion"),
        item_ids=child_ids,
    )


def _head(
    items: tuple[NativeExamItem, ...], parents: tuple[NativeExamParent, ...]
) -> NativeExamDocument:
    """A v7 head rebuilt through the production model, parents included."""
    return NativeExamDocument.model_validate(
        make_document(*items).model_dump() | {"parents": [p.model_dump() for p in parents]}
    )


def _item_ids(members: list[OutlineMember]) -> list[str]:
    return [member.item.item_id for member in members if isinstance(member, MemberItem)]


def _head_with_two_children_and_a_standalone_question() -> NativeExamDocument:
    return _head(
        items=(
            make_free_text_item(sequence=1, item_id="item_001"),
            make_free_text_item(sequence=2, item_id="item_002"),
            make_free_text_item(sequence=3, item_id="item_003"),
        ),
        parents=(_part("parent_001", 0, "item_001", "item_002"),),
    )


def test_insert_after_a_non_final_child_joins_the_part() -> None:
    head = _head_with_two_children_and_a_standalone_question()
    inserted = make_free_text_item(item_id="item_100")

    members = merged_members(
        head=head,
        replacements={},
        removed=set(),
        inserts=[("item_001", (inserted,))],
    )

    assert _item_ids(members) == ["item_001", "item_100", "item_002", "item_003"]
    assert isinstance(members[1], MemberItem)
    assert members[1].part is not None
    assert members[1].part.parent_id == "parent_001"


def test_insert_after_the_final_child_before_a_standalone_question_is_standalone() -> None:
    head = _head_with_two_children_and_a_standalone_question()
    inserted = make_free_text_item(item_id="item_100")

    members = merged_members(
        head=head,
        replacements={},
        removed=set(),
        inserts=[("item_002", (inserted,))],
    )

    assert _item_ids(members) == ["item_001", "item_002", "item_100", "item_003"]
    assert isinstance(members[2], MemberItem)
    assert members[2].part is None


def test_insert_right_before_a_childless_block_is_standalone() -> None:
    head = _head(
        items=(make_free_text_item(sequence=1, item_id="item_001"),),
        parents=(
            _part("parent_001", 0, "item_001"),
            _part("parent_002", 1),
        ),
    )
    inserted = make_free_text_item(item_id="item_100")

    members = merged_members(
        head=head,
        replacements={},
        removed=set(),
        inserts=[("item_001", (inserted,))],
    )

    assert _item_ids(members) == ["item_001", "item_100"]
    assert isinstance(members[1], MemberItem)
    assert members[1].part is None
    assert isinstance(members[2], MemberBlock)
    assert members[2].part.parent_id == "parent_002"
