"""Merge progressive DOCX conversion results into the saved head (TASK-SKRIPT-39-05-04 D30).

A conversion unit is one outline question, or one review item for a source chunk no
question owns. Each unit remembers the item ids and a digest of the items conversion
last wrote. A later result replaces a unit's items in the head only while the head still
holds exactly those items; once the teacher changed, removed or reordered them, the
teacher's version stays and the late result is dropped. The document title, the
instructions and the parents follow the same rule. Items the teacher added belong to no
unit and keep their place.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamItem,
    NativeExamParent,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    validate_parent_structure,
)
from skriptoteket.protocols.docx_conversion_progress import ConversionUpdate

_FRESH_ITEM_ID_FLOOR = 1000
_ITEM_ID_CEILING = 9999


class ConversionUnitState(StrEnum):
    CONVERTING = "converting"
    READY = "ready"
    TEACHER_KEPT = "teacher_kept"


class ConversionUnit(BaseModel):
    """Items conversion last wrote for one unit, identified by their digest."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    unit_id: str
    question: bool
    state: ConversionUnitState
    item_ids: tuple[str, ...] = ()
    digest: str | None = None


class ConversionProgress(BaseModel):
    """Progressive conversion state stored on the job row."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    units: tuple[ConversionUnit, ...] = ()
    revision: int | None = Field(default=None, ge=1)
    title_digest: str | None = None
    instructions_digest: str | None = None
    parents_digest: str | None = None

    @classmethod
    def from_question_ids(cls, question_ids: Iterable[str]) -> ConversionProgress:
        return cls(
            units=tuple(
                ConversionUnit(
                    unit_id=question_id, question=True, state=ConversionUnitState.CONVERTING
                )
                for question_id in question_ids
            )
        )

    @property
    def questions_total(self) -> int:
        return sum(unit.question for unit in self.units)

    @property
    def questions_done(self) -> int:
        return sum(
            unit.question and unit.state is not ConversionUnitState.CONVERTING
            for unit in self.units
        )


@dataclass(frozen=True)
class CandidateUnit:
    unit_id: str
    question: bool
    state: ConversionUnitState
    items: tuple[NativeExamItem, ...]


@dataclass(frozen=True)
class ConversionTarget:
    """A conversion result to merge; a field left as None keeps the head's value."""

    units: tuple[CandidateUnit, ...]
    title: str | None = None
    instructions: tuple[str, ...] | None = None
    parents: tuple[NativeExamParent, ...] | None = None


@dataclass(frozen=True)
class ConversionMerge:
    document: NativeExamDocument
    progress: ConversionProgress
    changed: bool


def _digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def items_digest(items: Sequence[NativeExamItem]) -> str:
    """Item content without ids and positions, so renumbering never reads as an edit."""
    return _digest(
        [item.model_dump(mode="json", exclude={"item_id", "sequence"}) for item in items]
    )


def _parents_digest(parents: Sequence[NativeExamParent]) -> str:
    return _digest([parent.model_dump(mode="json") for parent in parents])


def target_from_update(update: ConversionUpdate) -> ConversionTarget:
    """Units in document order: outline questions plus one unit per question-less item."""
    by_id = {item.item_id: item for item in update.document.items}
    position = {item.item_id: index for index, item in enumerate(update.document.items)}
    pending = set(update.pending)
    units = [
        CandidateUnit(
            unit_id=question_id,
            question=True,
            state=(
                ConversionUnitState.CONVERTING
                if question_id in pending
                else ConversionUnitState.READY
            ),
            items=tuple(by_id[item_id] for item_id in item_ids),
        )
        for question_id, item_ids in update.item_ids.items()
    ]
    units.extend(
        CandidateUnit(
            unit_id=f"extra:{by_id[item_id].source_anchor or item_id}",
            question=False,
            state=ConversionUnitState.READY,
            items=(by_id[item_id],),
        )
        for item_id in update.extra_item_ids
    )
    units.sort(key=lambda unit: min((position[i.item_id] for i in unit.items), default=0))
    return ConversionTarget(
        units=tuple(units),
        title=update.document.title,
        instructions=update.document.instructions,
        parents=update.document.parents,
    )


def first_conversion(*, update: ConversionUpdate, progress: ConversionProgress) -> ConversionMerge:
    """The first saved revision is the provisional document itself."""
    target = target_from_update(update)
    written = {
        unit.unit_id: ConversionUnit(
            unit_id=unit.unit_id,
            question=unit.question,
            state=unit.state,
            item_ids=tuple(item.item_id for item in unit.items),
            digest=items_digest(unit.items),
        )
        for unit in target.units
    }
    document = update.document.model_copy(update={"revision": 1})
    return ConversionMerge(
        document=document,
        progress=ConversionProgress(
            units=_ordered_units(progress, written),
            revision=1,
            title_digest=_digest(document.title),
            instructions_digest=_digest(list(document.instructions)),
            parents_digest=_parents_digest(document.parents),
        ),
        changed=True,
    )


def abandon_target(
    *, head: NativeExamDocument, progress: ConversionProgress, reason: str
) -> ConversionTarget:
    """Turn every still-converting unit into review items that carry the failure reason."""
    by_id = {item.item_id: item for item in head.items}
    units = []
    for unit in progress.units:
        if unit.state is not ConversionUnitState.CONVERTING or unit.digest is None:
            continue
        items = tuple(
            by_id[item_id].model_copy(
                update={"review": by_id[item_id].review.model_copy(update={"reasons": (reason,)})}
            )
            for item_id in unit.item_ids
            if item_id in by_id
        )
        units.append(
            CandidateUnit(
                unit_id=unit.unit_id,
                question=unit.question,
                state=ConversionUnitState.READY,
                items=items,
            )
        )
    return ConversionTarget(units=tuple(units))


class _ItemIds:
    """Fresh item ids above the teacher's own numbering, so concurrent additions never clash."""

    def __init__(self, used: Iterable[str]) -> None:
        self._used = set(used)
        numbers = [int(item_id[5:]) for item_id in self._used if item_id[5:].isdigit()]
        self._next = max([_FRESH_ITEM_ID_FLOOR, *numbers]) + 1

    def reserve(self, item_id: str) -> None:
        self._used.add(item_id)

    def fresh(self) -> str:
        while f"item_{self._next}" in self._used:
            self._next += 1
        if self._next > _ITEM_ID_CEILING:
            raise ValueError("no free item id left in the document")
        item_id = f"item_{self._next}"
        self._used.add(item_id)
        return item_id


def _ordered_units(
    progress: ConversionProgress, written: dict[str, ConversionUnit]
) -> tuple[ConversionUnit, ...]:
    known = [written.get(unit.unit_id, unit) for unit in progress.units]
    known_ids = {unit.unit_id for unit in progress.units}
    return (*known, *(unit for unit_id, unit in written.items() if unit_id not in known_ids))


def merge_conversion(
    *, head: NativeExamDocument, progress: ConversionProgress, target: ConversionTarget
) -> ConversionMerge:
    """Apply ``target`` to ``head`` unit by unit; the teacher's edits always win."""
    head_by_id = {item.item_id: item for item in head.items}
    known = {unit.unit_id: unit for unit in progress.units}
    ids = _ItemIds(head_by_id)
    id_map: dict[str, str] = {}
    replacements: dict[str, tuple[NativeExamItem, ...]] = {}
    removed: set[str] = set()
    inserts: list[tuple[str | None, tuple[NativeExamItem, ...]]] = []
    written: dict[str, ConversionUnit] = {}
    previous_last: str | None = None

    for candidate in target.units:
        prior = known.get(candidate.unit_id)
        candidate_digest = items_digest(candidate.items)
        if prior is None or prior.digest is None:
            placed = tuple(
                item.model_copy(update={"item_id": ids.fresh()}) for item in candidate.items
            )
            inserts.append((previous_last, placed))
            written[candidate.unit_id] = ConversionUnit(
                unit_id=candidate.unit_id,
                question=candidate.question,
                state=candidate.state,
                item_ids=tuple(item.item_id for item in placed),
                digest=candidate_digest,
            )
            id_map.update(
                zip(
                    (i.item_id for i in candidate.items),
                    written[candidate.unit_id].item_ids,
                    strict=True,
                )
            )
            previous_last = placed[-1].item_id if placed else previous_last
            continue
        head_items = tuple(head_by_id[i] for i in prior.item_ids if i in head_by_id)
        intact = len(head_items) == len(prior.item_ids) and items_digest(head_items) == prior.digest
        if intact and candidate_digest != prior.digest:
            new_ids = [*prior.item_ids[: len(candidate.items)]]
            new_ids.extend(ids.fresh() for _ in range(len(candidate.items) - len(new_ids)))
            placed = tuple(
                item.model_copy(update={"item_id": item_id})
                for item, item_id in zip(candidate.items, new_ids, strict=True)
            )
            if placed:
                replacements[prior.item_ids[0]] = placed
            removed.update(prior.item_ids)
            written[candidate.unit_id] = prior.model_copy(
                update={
                    "state": candidate.state,
                    "item_ids": tuple(new_ids),
                    "digest": candidate_digest,
                }
            )
            id_map.update(zip((i.item_id for i in candidate.items), new_ids, strict=True))
            previous_last = new_ids[-1] if new_ids else previous_last
            continue
        if intact:
            id_map.update(zip((i.item_id for i in candidate.items), prior.item_ids, strict=True))
            written[candidate.unit_id] = prior.model_copy(update={"state": candidate.state})
        else:
            # The teacher's items stay, and stay under the parents conversion gives them.
            id_map.update(
                (item.item_id, item_id)
                for item, item_id in zip(candidate.items, prior.item_ids, strict=False)
                if item_id in head_by_id
            )
            if prior.state is ConversionUnitState.CONVERTING:
                written[candidate.unit_id] = prior.model_copy(
                    update={"state": ConversionUnitState.TEACHER_KEPT}
                )
        previous_last = head_items[-1].item_id if head_items else previous_last

    ordered: list[NativeExamItem] = []
    for item in head.items:
        if item.item_id in replacements:
            ordered.extend(replacements[item.item_id])
        elif item.item_id not in removed:
            ordered.append(item)
    for after, placed in inserts:
        index = next(
            (position + 1 for position, item in enumerate(ordered) if item.item_id == after), 0
        )
        ordered[index:index] = placed
    items = tuple(
        item.model_copy(update={"sequence": sequence})
        for sequence, item in enumerate(ordered, start=1)
    )

    title, title_digest = _choose(head.title, target.title, progress.title_digest)
    instructions, instructions_digest = _choose(
        head.instructions, target.instructions, progress.instructions_digest
    )
    parents, parents_digest = _merge_parents(head, target, progress, id_map, items)
    document = head.model_copy(
        update={
            "revision": head.revision + 1,
            "title": title,
            "instructions": instructions,
            "items": items,
            "parents": parents,
        }
    )
    document = NativeExamDocument.model_validate(document.model_dump())
    changed = document.model_dump(exclude={"revision"}) != head.model_dump(exclude={"revision"})
    return ConversionMerge(
        document=document,
        progress=progress.model_copy(
            update={
                "units": _ordered_units(progress, written),
                "title_digest": title_digest,
                "instructions_digest": instructions_digest,
                "parents_digest": parents_digest,
            }
        ),
        changed=changed,
    )


def _choose[T: (str, tuple[str, ...])](
    current: T, proposed: T | None, delivered_digest: str | None
) -> tuple[T, str | None]:
    if proposed is None:
        return current, delivered_digest
    as_json = list(current) if isinstance(current, tuple) else current
    if _digest(as_json) != delivered_digest:
        return current, delivered_digest
    proposed_json = list(proposed) if isinstance(proposed, tuple) else proposed
    return proposed, _digest(proposed_json)


def _merge_parents(
    head: NativeExamDocument,
    target: ConversionTarget,
    progress: ConversionProgress,
    id_map: dict[str, str],
    items: tuple[NativeExamItem, ...],
) -> tuple[tuple[NativeExamParent, ...], str | None]:
    """Conversion's parents while the teacher kept the delivered ones (D30).

    A parent whose saved children no longer form one consecutive run of one kind is split
    into such runs, each carrying the instruction (D27), so no child loses its instruction.
    """
    delivered = (
        target.parents is not None and _parents_digest(head.parents) == progress.parents_digest
    )
    if delivered and target.parents is not None:
        proposed = [
            parent.model_copy(
                update={"item_ids": tuple(id_map[i] for i in parent.item_ids if i in id_map)}
            )
            for parent in target.parents
        ]
    else:
        proposed = list(head.parents)
    by_id = {item.item_id: item for item in items}
    parent_ids = _ParentIds(parent.parent_id for parent in proposed)
    claimed: set[str] = set()
    accepted: list[NativeExamParent] = []
    for parent in proposed:
        children = sorted(
            (by_id[i] for i in dict.fromkeys(parent.item_ids) if i in by_id and i not in claimed),
            key=lambda item: item.sequence,
        )
        for index, run in enumerate(_kind_runs(children)):
            parent_id = parent.parent_id if index == 0 else parent_ids.fresh()
            accepted.append(parent.model_copy(update={"parent_id": parent_id, "item_ids": run}))
            claimed.update(run)
    parents = tuple(accepted)
    validate_parent_structure(parents, items)
    return parents, (_parents_digest(parents) if delivered else progress.parents_digest)


def _kind_runs(children: Sequence[NativeExamItem]) -> list[tuple[str, ...]]:
    """Maximal runs of children that are consecutive in the document and share one kind."""
    runs: list[list[NativeExamItem]] = []
    for child in children:
        last = runs[-1][-1] if runs else None
        if last is not None and child.sequence == last.sequence + 1 and child.kind is last.kind:
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
