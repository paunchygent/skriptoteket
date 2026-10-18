"""The one ordering owner for the exam document's parts and questions (R1).

Governing decisions: TASK-SKRIPT-39-06-10 (G5, G6, R1). The document stores each part's own
place in the document order and its children's ids; this module is the single place that
reads that stored form as an ordered outline and writes an outline back to item sequences
and part places. Every reader that needs document order -- commands, exporters, printers and
the left column -- reads the outline instead of guessing a part's position from its first
question.
"""

from __future__ import annotations

from collections.abc import Sequence
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
