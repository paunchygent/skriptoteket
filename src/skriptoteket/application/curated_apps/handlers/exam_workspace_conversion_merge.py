"""Merge progressive DOCX conversion results into the saved head (TASK-SKRIPT-39-05-04 D30).

A conversion unit is one outline question, or one review item for a source chunk no
question owns. Each unit remembers the item ids and a digest of the items conversion
last wrote. A still-converting unit's placeholders belong to conversion: the save handler
refuses a save that changes, moves or removes one (``changed_placeholders``), so a later
result always finds them intact and replaces them. A converted unit belongs to the
teacher: a later result replaces its items only while the head still holds exactly those
items, and once the teacher changed, removed or reordered them, the teacher's version
stays. The document title and the instructions follow the converted-unit rule. The parents
become a flat member list that the outline owner groups into parts and places (R1), so the
merge never computes a part place. Items the teacher added belong to no unit and keep their
place.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_merge_assets import (
    merged_assets,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_merge_fields import (
    choose_delivered_field as _choose,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_merge_fields import (
    digest_json as _digest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_merge_parents import (
    ParentIds,
    merged_members,
    parents_digest,
    with_delivered_membership,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
    NativeExamHeader,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_outline import (
    outline_from_members,
    outline_items_and_parts,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
    validate_parent_structure,
)
from skriptoteket.protocols.docx_conversion_progress import ConversionUpdate

_FRESH_ITEM_ID_FLOOR = 1000
_ITEM_ID_CEILING = 9999


class ConversionUnitState(StrEnum):
    CONVERTING = "converting"
    READY = "ready"


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
    received_question_ids: tuple[str, ...] = ()
    revision: int | None = Field(default=None, ge=1)
    title_digest: str | None = None
    header_digest: str | None = None
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
    def questions_received(self) -> int:
        return len(self.received_question_ids)

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
    header: NativeExamHeader | None = None
    instructions: tuple[NativeParagraph, ...] | None = None
    parents: tuple[NativeExamParent, ...] | None = None
    assets: tuple[NativeExamAsset, ...] | None = None


@dataclass(frozen=True)
class ConversionMerge:
    document: NativeExamDocument
    progress: ConversionProgress
    changed: bool


def items_digest(items: Sequence[NativeExamItem]) -> str:
    """Item content without ids and positions, so renumbering never reads as an edit."""
    return _digest(
        [item.model_dump(mode="json", exclude={"item_id", "sequence"}) for item in items]
    )


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
        header=update.document.header,
        instructions=update.document.instructions,
        parents=update.document.parents,
        assets=update.document.assets,
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
            received_question_ids=progress.received_question_ids,
            revision=1,
            title_digest=_digest(document.title),
            header_digest=_digest(document.header.model_dump(mode="json")),
            instructions_digest=_digest(
                [paragraph.model_dump(mode="json") for paragraph in document.instructions]
            ),
            parents_digest=parents_digest(document.parents),
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


def changed_placeholders(
    *, progress: ConversionProgress, base: NativeExamDocument, saved: NativeExamDocument
) -> list[str]:
    """Placeholder ids of ``base`` that ``saved`` changed, moved or removed, in base order.

    A placeholder moves when its parent or the order of the items both revisions hold
    around it changes; items the teacher added elsewhere move nothing.
    """
    locked = {
        item_id
        for unit in progress.units
        if unit.state is ConversionUnitState.CONVERTING and unit.digest is not None
        for item_id in unit.item_ids
    }
    saved_by_id = {item.item_id: item for item in saved.items}
    base_ids = {item.item_id for item in base.items}
    shared = [item.item_id for item in base.items if item.item_id in saved_by_id]
    saved_order = [item.item_id for item in saved.items if item.item_id in base_ids]

    def preceding(order: list[str], item_id: str) -> set[str]:
        return set(order[: order.index(item_id)])

    changed: list[str] = []
    for item in base.items:
        if item.item_id not in locked:
            continue
        counterpart = saved_by_id.get(item.item_id)
        if (
            counterpart is None
            or items_digest([counterpart]) != items_digest([item])
            or _parent_id(saved, item.item_id) != _parent_id(base, item.item_id)
            or preceding(saved_order, item.item_id) != preceding(shared, item.item_id)
        ):
            changed.append(item.item_id)
    return changed


def _parent_id(document: NativeExamDocument, item_id: str) -> str | None:
    parent = document.parent_of(item_id)
    return None if parent is None else parent.parent_id


def merge_conversion(
    *, head: NativeExamDocument, progress: ConversionProgress, target: ConversionTarget
) -> ConversionMerge:
    """Apply ``target`` to ``head`` unit by unit (see the module docstring for the rule)."""
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
            new_ids = list(prior.item_ids[: len(candidate.items)])
            new_ids.extend(ids.fresh() for _ in range(len(candidate.items) - len(new_ids)))
            placed = tuple(
                item.model_copy(update={"item_id": item_id})
                for item, item_id in zip(candidate.items, new_ids, strict=True)
            )
            if placed and prior.item_ids:
                replacements[prior.item_ids[0]] = placed
            elif placed:
                inserts.append((previous_last, placed))
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
            # The teacher's converted items stay, under the parents conversion gives them.
            id_map.update(
                (item.item_id, item_id)
                for item, item_id in zip(candidate.items, prior.item_ids, strict=False)
                if item_id in head_by_id
            )
        previous_last = head_items[-1].item_id if head_items else previous_last

    delivered = (
        target.parents is not None and parents_digest(head.parents) == progress.parents_digest
    )
    members = merged_members(head=head, replacements=replacements, removed=removed, inserts=inserts)
    if delivered and target.parents is not None:
        members = with_delivered_membership(members, proposed=target.parents, id_map=id_map)
    parent_ids = ParentIds(parent.parent_id for parent in (*head.parents, *(target.parents or ())))
    items, parents = outline_items_and_parts(outline_from_members(members, parent_ids.fresh))
    validate_parent_structure(parents, items)
    delivered_parents_digest = parents_digest(parents) if delivered else progress.parents_digest
    title, title_digest = _choose(head.title, target.title, progress.title_digest)
    # Assembly IDs are local to this target. Only this merge knows which saved
    # identities survive teacher edits and split-question placeholder replacement.
    proposed_header = target.header
    if proposed_header is not None:
        surviving_ids = {item.item_id for item in items}
        proposed_header = proposed_header.model_copy(
            update={
                "tags": tuple(
                    tag.model_copy(
                        update={
                            "question_ids": tuple(
                                id_map[value]
                                for value in tag.question_ids
                                if value in id_map and id_map[value] in surviving_ids
                            )
                        }
                    )
                    for tag in proposed_header.tags
                )
            }
        )
    header, header_digest = _choose(head.header, proposed_header, progress.header_digest)
    instructions, instructions_digest = _choose(
        head.instructions, target.instructions, progress.instructions_digest
    )
    assets = merged_assets(
        head=head,
        delivered=target.assets,
        items=items,
        instructions=instructions,
        parents=parents,
    )
    document = head.model_copy(
        update={
            "revision": head.revision + 1,
            "title": title,
            "header": header,
            "instructions": instructions,
            "items": items,
            "parents": parents,
            "assets": assets,
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
                "header_digest": header_digest,
                "instructions_digest": instructions_digest,
                "parents_digest": delivered_parents_digest,
            }
        ),
        changed=changed,
    )
