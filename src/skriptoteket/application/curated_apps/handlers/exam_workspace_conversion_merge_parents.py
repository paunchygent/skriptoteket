"""Conversion's part membership as a flat member list; the outline owner assigns places (R1).

The merge never computes a part ``place``. It walks the head's outline as members and produces
one member per item, carrying the part the item belongs to, plus one block per childless part;
``native_exam_outline`` groups the members into parts with places.
"""

from collections.abc import Iterable, Sequence

from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_merge_fields import (
    digest_json,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_outline import (
    MemberBlock,
    MemberItem,
    OutlineMember,
    document_outline,
    outline_members,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
)


def parents_digest(parents: Sequence[NativeExamParent]) -> str:
    return digest_json([parent.model_dump(mode="json") for parent in parents])


def merged_members(
    *,
    head: NativeExamDocument,
    replacements: dict[str, tuple[NativeExamItem, ...]],
    removed: set[str],
    inserts: list[tuple[str | None, tuple[NativeExamItem, ...]]],
) -> list[OutlineMember]:
    """The head's members with converted units applied (F1 slot substitution).

    A replaced item becomes one member per converted item, each keeping the replaced item's
    part, so an expanded question stays inside its part's slot. A removed item drops. An
    inserted unit joins the part of the member before it only when the next item member carries
    that same part; otherwise it is standalone.
    """
    members: list[OutlineMember] = []
    for member in outline_members(document_outline(head)):
        if isinstance(member, MemberItem):
            if member.item.item_id in replacements:
                members.extend(
                    MemberItem(item=item, part=member.part)
                    for item in replacements[member.item.item_id]
                )
                continue
            if member.item.item_id in removed:
                continue
        members.append(member)
    for after, placed in inserts:
        index = next(
            (
                position + 1
                for position, member in enumerate(members)
                if isinstance(member, MemberItem) and member.item.item_id == after
            ),
            0,
        )
        part = _insert_part(members, index)
        members[index:index] = [MemberItem(item=item, part=part) for item in placed]
    return members


def _insert_part(members: Sequence[OutlineMember], index: int) -> NativeExamParent | None:
    """The part an inserted unit joins: the part both its neighbours carry.

    It joins the part of the member immediately before ``index`` only when that member and
    the member immediately at ``index`` are both item members carrying the same part;
    otherwise it is standalone (R1). This is the server twin of the client merge's
    ``neighbourParentId``: a block between the neighbours makes the unit standalone.
    """
    if index == 0 or index >= len(members):
        return None
    before = members[index - 1]
    after = members[index]
    if not isinstance(before, MemberItem) or not isinstance(after, MemberItem):
        return None
    if before.part is None or after.part is None:
        return None
    if before.part.parent_id != after.part.parent_id:
        return None
    return before.part


def with_delivered_membership(
    members: Sequence[OutlineMember],
    *,
    proposed: tuple[NativeExamParent, ...],
    id_map: dict[str, str],
) -> list[OutlineMember]:
    """Members' parts from the delivered parents, by item id through ``id_map`` (D30).

    The teacher kept the delivered parents, so each merged item takes the delivered part that
    owns it; an item no delivered part owns belongs to none. Block members keep their part.
    """
    owner: dict[str, NativeExamParent] = {}
    for parent in proposed:
        for item_id in parent.item_ids:
            mapped = id_map.get(item_id)
            if mapped is not None:
                owner[mapped] = parent
    result: list[OutlineMember] = []
    for member in members:
        if isinstance(member, MemberBlock):
            result.append(member)
            continue
        result.append(MemberItem(item=member.item, part=owner.get(member.item.item_id)))
    return result


class ParentIds:
    """Fresh parent ids for the runs a split part adds."""

    def __init__(self, used: Iterable[str]) -> None:
        self._used = set(used)
        self._next = max([0, *(int(p[7:]) for p in self._used if p[7:].isdigit())]) + 1

    def fresh(self) -> str:
        while f"parent_{self._next:03d}" in self._used:
            self._next += 1
        parent_id = f"parent_{self._next:03d}"
        self._used.add(parent_id)
        return parent_id
