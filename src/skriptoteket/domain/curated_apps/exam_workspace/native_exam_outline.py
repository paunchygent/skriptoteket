"""The one ordering owner for the exam document's parts and questions (R1).

Governing decisions: TASK-SKRIPT-39-06-10 (G5, G6, R1). The document stores each part's own
place in the document order and its children's ids; this module is the single place that
reads that stored form as an ordered outline and writes an outline back to item sequences
and part places. Every reader that needs document order -- commands, exporters, printers and
the left column -- reads the outline instead of guessing a part's position from its first
question.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
        NativeExamDocument,
    )
    from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
        NativeExamItem,
    )
    from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
        NativeExamParent,
    )


@dataclass(frozen=True, slots=True)
class OutlineQuestion:
    """A standalone question: an item that belongs to no part."""

    item: NativeExamItem


@dataclass(frozen=True, slots=True)
class OutlinePart:
    """A part in document order with its children, empty for an instruction block."""

    part: NativeExamParent
    children: tuple[NativeExamItem, ...]


OutlineEntry = OutlineQuestion | OutlinePart


@dataclass(frozen=True, slots=True)
class MemberItem:
    """One item token in the member list, with the part it belongs to (None: standalone)."""

    item: NativeExamItem
    part: NativeExamParent | None


@dataclass(frozen=True, slots=True)
class MemberBlock:
    """One childless part token in the member list, at its position among the items."""

    part: NativeExamParent


OutlineMember = MemberItem | MemberBlock


def document_outline(document: NativeExamDocument) -> tuple[OutlineEntry, ...]:
    """Top-level entries in document order: standalone questions and parts with their children."""
    items = document.items
    item_by_id = {item.item_id: item for item in items}
    parent_by_item: dict[str, NativeExamParent] = {}
    parents_by_place: dict[int, list[NativeExamParent]] = {}
    for parent in document.parents:
        parents_by_place.setdefault(parent.place, []).append(parent)
        for item_id in parent.item_ids:
            parent_by_item[item_id] = parent
    entries: list[OutlineEntry] = []
    index = 0
    while index < len(items):
        for parent in parents_by_place.get(index, ()):
            entries.append(_outline_part(parent, item_by_id))
        item = items[index]
        owner = parent_by_item.get(item.item_id)
        if owner is None:
            entries.append(OutlineQuestion(item=item))
            index += 1
        else:
            index += len(owner.item_ids)
    for parent in parents_by_place.get(len(items), ()):
        entries.append(_outline_part(parent, item_by_id))
    return tuple(entries)


def _outline_part(
    parent: NativeExamParent,
    item_by_id: dict[str, NativeExamItem],
) -> OutlinePart:
    return OutlinePart(
        part=parent, children=tuple(item_by_id[item_id] for item_id in parent.item_ids)
    )


def outline_items_and_parts(
    outline: Sequence[OutlineEntry],
) -> tuple[tuple[NativeExamItem, ...], tuple[NativeExamParent, ...]]:
    """Items numbered 1..n in outline order and parts with place and item_ids from the outline."""
    items: list[NativeExamItem] = []
    parts: list[NativeExamParent] = []
    count = 0
    for entry in outline:
        if isinstance(entry, OutlineQuestion):
            count += 1
            items.append(entry.item.model_copy(update={"sequence": count}))
            continue
        parts.append(
            entry.part.model_copy(
                update={
                    "place": count,
                    "item_ids": tuple(child.item_id for child in entry.children),
                }
            )
        )
        for child in entry.children:
            count += 1
            items.append(child.model_copy(update={"sequence": count}))
    return tuple(items), tuple(parts)


def outline_members(outline: Sequence[OutlineEntry]) -> tuple[OutlineMember, ...]:
    """The outline as a flat member list: one item token per item, one block per childless part.

    This is the read half of the one grouping rule ``outline_from_members`` applies: an item
    token carries the part it belongs to (or none), and a childless part is a block token at its
    own position among the items.
    """
    members: list[OutlineMember] = []
    for entry in outline:
        if isinstance(entry, OutlinePart):
            if entry.children:
                members.extend(MemberItem(item=child, part=entry.part) for child in entry.children)
            else:
                members.append(MemberBlock(part=entry.part))
            continue
        members.append(MemberItem(item=entry.item, part=None))
    return tuple(members)


def outline_from_members(
    members: Sequence[OutlineMember],
    fresh_parent_id: Callable[[], str],
) -> tuple[OutlineEntry, ...]:
    """The one grouping rule: consecutive item tokens of one part form it (R1, D30).

    A block token becomes a childless part in place. Consecutive item tokens whose part shares a
    ``parent_id`` become one part entry; when the same original ``parent_id`` reappears after an
    interruption, each later run is a copy of the part with a fresh id that carries the same
    instruction, so no child loses its part. Returned entries keep the member order.
    """
    entries: list[OutlineEntry] = []
    run_part: NativeExamParent | None = None
    run_children: list[NativeExamItem] = []
    started: set[str] = set()

    def flush() -> None:
        nonlocal run_part, run_children
        if run_part is None:
            return
        part = run_part
        if part.parent_id in started:
            part = part.model_copy(update={"parent_id": fresh_parent_id()})
        started.add(run_part.parent_id)
        entries.append(OutlinePart(part=part, children=tuple(run_children)))
        run_part = None
        run_children = []

    for member in members:
        if isinstance(member, MemberBlock):
            flush()
            entries.append(OutlinePart(part=member.part, children=()))
            continue
        if member.part is None:
            flush()
            entries.append(OutlineQuestion(item=member.item))
            continue
        if run_part is None or run_part.parent_id != member.part.parent_id:
            flush()
            run_part = member.part
        run_children.append(member.item)
    flush()
    return tuple(entries)
