"""Parents of the native exam document: shared instructions over consecutive child items.

Governing decisions: TASK-SKRIPT-39-05-03 rule 7 and D10, ST-SKRIPT-39-06 P4. A parent
owns no points and no answer key; each child item keeps its own. Parent structure and
point aggregation live here, independently of item-kind validation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, model_validator

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
)

if TYPE_CHECKING:
    from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
        NativeExamDocument,
    )
    from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
        NativeExamItem,
    )

_PARENT_ID_PATTERN = r"^parent_[0-9]{3}$"


class NativeExamParent(BaseModel):
    """A part: shared instruction over child items, or an instruction block with none.

    A parent owns no points and no answer key: each child item keeps its own kind, points
    and answer key, as an Exam.net information block holds questions of any type (D27).
    ``place`` is the part's own stored place in the document order: the number of questions
    that come before it (G5, R1). ``item_ids`` may be empty, so a part with no questions is
    an instruction block that keeps its position. ``printed_total`` is the part total the
    source prints over these children; it is compared with their points and never shown as
    instruction text (TASK-SKRIPT-39-05-14). Its instruction is one body of positioned
    paragraphs: the shared wording with every shared picture at its exact source place (F2),
    never a gap the student fills.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    parent_id: str = Field(pattern=_PARENT_ID_PATTERN)
    place: int = Field(ge=0)
    instruction: tuple[NativeParagraph, ...]  # empty: the parent prints no instruction
    item_ids: tuple[str, ...] = ()
    printed_total: int | float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _instruction_is_shared_text(self) -> "NativeExamParent":
        for paragraph in self.instruction:
            for segment in paragraph.segments:
                if isinstance(segment, NativeGapSegment):
                    raise ValueError("a parent instruction cannot place a gap")
        return self


def validate_parent_structure(
    parents: tuple[NativeExamParent, ...],
    items: tuple[NativeExamItem, ...],
) -> None:
    """Every part's stored place agrees with the document order of its children.

    The ``parents`` tuple is itself in document order: places are non-decreasing. A part
    sits at the number of questions before it (``place``), and its children are the
    consecutive items that start directly after that place. A part may hold no children and
    still keep its place. No part's place may fall between another part's children, and at
    one place a part with children comes last so no other part splits its children.
    """
    parent_ids = [parent.parent_id for parent in parents]
    if len(set(parent_ids)) != len(parent_ids):
        raise ValueError("parent ids must be unique")
    item_by_id = {item.item_id: item for item in items}
    item_count = len(items)
    claimed: set[str] = set()
    previous_place: int | None = None
    for parent in parents:
        if parent.place > item_count:
            raise ValueError(
                f"parent {parent.parent_id} place {parent.place} is beyond the document's "
                f"{item_count} items"
            )
        if previous_place is not None and parent.place < previous_place:
            raise ValueError("parents must be in document order by place")
        previous_place = parent.place
        unknown = [item_id for item_id in parent.item_ids if item_id not in item_by_id]
        if unknown:
            raise ValueError(f"parent {parent.parent_id} references unknown items: {unknown}")
        overlap = claimed.intersection(parent.item_ids)
        if overlap:
            raise ValueError(f"items belong to more than one parent: {sorted(overlap)}")
        claimed.update(parent.item_ids)
        children = [item_by_id[item_id] for item_id in parent.item_ids]
        if not children:
            continue
        first = children[0].sequence
        if first != parent.place + 1:
            raise ValueError(
                f"parent {parent.parent_id} first child must come directly after its place"
            )
        if [child.sequence for child in children] != list(range(first, first + len(children))):
            raise ValueError(
                f"parent {parent.parent_id} children must be consecutive items in sequence order"
            )
    _refuse_place_inside_children(parents)
    _refuse_childless_part_after_children(parents)


def _refuse_place_inside_children(parents: tuple[NativeExamParent, ...]) -> None:
    """No part's place may fall strictly between another part's children."""
    for parent in parents:
        if not parent.item_ids:
            continue
        end = parent.place + len(parent.item_ids)
        for other in parents:
            if other is parent:
                continue
            if parent.place < other.place < end:
                raise ValueError(
                    f"parent {other.parent_id} place {other.place} falls inside parent "
                    f"{parent.parent_id}'s children"
                )


def _refuse_childless_part_after_children(parents: tuple[NativeExamParent, ...]) -> None:
    """At one place, a childless part must be listed before the parts with children."""
    for earlier, later in zip(parents, parents[1:], strict=False):
        if earlier.place == later.place and earlier.item_ids and not later.item_ids:
            raise ValueError(
                f"parent {later.parent_id} has no children and must come before the parts "
                f"with children at place {later.place}"
            )


def parent_points(document: NativeExamDocument, parent: NativeExamParent) -> int | float | None:
    """Sum of the children's points; 0 with no children, None when any child has no points."""
    total: int | float = 0
    for item_id in parent.item_ids:
        points = document.item_by_id(item_id).points
        if points is None:
            return None
        total += points
    return total
