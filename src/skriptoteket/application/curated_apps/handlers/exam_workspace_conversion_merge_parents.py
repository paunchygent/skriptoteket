"""Reconcile delivered parents with saved children and teacher-owned parent edits."""

from collections.abc import Iterable, Sequence

from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_merge_fields import (
    digest_json,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
    validate_parent_structure,
)


def parents_digest(parents: Sequence[NativeExamParent]) -> str:
    return digest_json([parent.model_dump(mode="json") for parent in parents])


def merge_parents(
    *,
    current: tuple[NativeExamParent, ...],
    proposed: tuple[NativeExamParent, ...] | None,
    delivered_digest: str | None,
    id_map: dict[str, str],
    items: tuple[NativeExamItem, ...],
    head_items: tuple[NativeExamItem, ...],
) -> tuple[tuple[NativeExamParent, ...], str | None]:
    """Conversion's parents while the teacher kept the delivered ones (D30).

    A parent whose saved children no longer form one consecutive run is split into such runs,
    each carrying the instruction, so no child loses its instruction. Children of any kinds
    share a parent (D27). A part with no children is a teacher-made instruction block: it keeps
    the place it held before the merge, anchored to the saved question before it.
    """
    delivered = proposed is not None and parents_digest(current) == delivered_digest
    if delivered and proposed is not None:
        candidates = [
            (
                parent.model_copy(
                    update={"item_ids": tuple(id_map[i] for i in parent.item_ids if i in id_map)}
                ),
                bool(parent.item_ids),
            )
            for parent in proposed
        ]
    else:
        candidates = [(parent, bool(parent.item_ids)) for parent in current]
    by_id = {item.item_id: item for item in items}
    position = {item.item_id: index for index, item in enumerate(items)}
    parent_ids = _ParentIds(parent.parent_id for parent, _ in candidates)
    claimed: set[str] = set()
    child_parts: list[NativeExamParent] = []
    blocks: list[NativeExamParent] = []
    placed_blocks: list[NativeExamParent] = []
    for parent, had_children in candidates:
        if not parent.item_ids:
            # A delivered part loses every child when the merge drops them all.
            if not had_children:
                blocks.append(parent)
            continue
        children = sorted(
            (by_id[i] for i in dict.fromkeys(parent.item_ids) if i in by_id and i not in claimed),
            key=lambda item: item.sequence,
        )
        for index, run in enumerate(_consecutive_runs(children)):
            parent_id = parent.parent_id if index == 0 else parent_ids.fresh()
            child_parts.append(
                parent.model_copy(
                    update={
                        "parent_id": parent_id,
                        "place": by_id[run[0]].sequence - 1,
                        "item_ids": run,
                    }
                )
            )
            claimed.update(run)
    for parent in blocks:
        place = next(
            (
                position[earlier.item_id] + 1
                for earlier in reversed(head_items[: parent.place])
                if earlier.item_id in position
            ),
            0,
        )
        for part in child_parts:
            if part.place < place < part.place + len(part.item_ids):
                place = part.place + len(part.item_ids)
        placed_blocks.append(parent.model_copy(update={"place": place, "item_ids": ()}))
    parents = tuple(
        sorted(
            (*child_parts, *placed_blocks),
            key=lambda parent: (parent.place, 0 if not parent.item_ids else 1),
        )
    )
    validate_parent_structure(parents, items)
    return parents, (parents_digest(parents) if delivered else delivered_digest)


def _consecutive_runs(children: Sequence[NativeExamItem]) -> list[tuple[str, ...]]:
    """Maximal runs of children that are consecutive in the document."""
    runs: list[list[NativeExamItem]] = []
    for child in children:
        last = runs[-1][-1] if runs else None
        if last is not None and child.sequence == last.sequence + 1:
            runs[-1].append(child)
        else:
            runs.append([child])
    return [tuple(child.item_id for child in run) for run in runs]


class _ParentIds:
    """Fresh parent ids for the runs a split parent adds."""

    def __init__(self, used: Iterable[str]) -> None:
        self._used = set(used)
        self._next = max([0, *(int(p[7:]) for p in self._used if p[7:].isdigit())]) + 1

    def fresh(self) -> str:
        while f"parent_{self._next:03d}" in self._used:
            self._next += 1
        parent_id = f"parent_{self._next:03d}"
        self._used.add(parent_id)
        return parent_id
