"""Parents of the native exam document: shared instructions over consecutive child items.

Governing decisions: TASK-SKRIPT-39-05-03 rule 7 and D10, ST-SKRIPT-39-06 P4. A parent
owns no points and no answer key; each child item keeps its own. The document re-exports
these names from `native_exam_document`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
        NativeExamDocument,
        NativeExamItem,
    )

_PARENT_ID_PATTERN = r"^parent_[0-9]{3}$"


class NativeExamParent(BaseModel):
    """Shared instruction for a run of consecutive child items of any mix of kinds.

    A parent owns no points and no answer key: each child item keeps its own kind, points
    and answer key, as an Exam.net information block holds questions of any type (D27).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    parent_id: str = Field(pattern=_PARENT_ID_PATTERN)
    instruction: tuple[str, ...] = Field(min_length=1)
    item_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("instruction")
    @classmethod
    def _non_blank_lines(cls, lines: tuple[str, ...]) -> tuple[str, ...]:
        for line in lines:
            if not line.strip():
                raise ValueError("parent instruction lines must be non-blank")
        return lines


def validate_parent_structure(
    parents: tuple[NativeExamParent, ...],
    items: tuple[NativeExamItem, ...],
) -> None:
    """Children exist, belong to one parent and are consecutive in sequence order."""
    parent_ids = [parent.parent_id for parent in parents]
    if len(set(parent_ids)) != len(parent_ids):
        raise ValueError("parent ids must be unique")
    item_by_id = {item.item_id: item for item in items}
    claimed: set[str] = set()
    for parent in parents:
        unknown = [item_id for item_id in parent.item_ids if item_id not in item_by_id]
        if unknown:
            raise ValueError(f"parent {parent.parent_id} references unknown items: {unknown}")
        overlap = claimed.intersection(parent.item_ids)
        if overlap:
            raise ValueError(f"items belong to more than one parent: {sorted(overlap)}")
        claimed.update(parent.item_ids)
        children = [item_by_id[item_id] for item_id in parent.item_ids]
        first = children[0].sequence
        if [child.sequence for child in children] != list(range(first, first + len(children))):
            raise ValueError(
                f"parent {parent.parent_id} children must be consecutive items in sequence order"
            )


def parent_points(document: NativeExamDocument, parent: NativeExamParent) -> int | float | None:
    """Sum of the children's points; None when any child has no points."""
    total: int | float = 0
    for item_id in parent.item_ids:
        points = document.item_by_id(item_id).points
        if points is None:
            return None
        total += points
    return total
