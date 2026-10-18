"""Teacher parent commands over immutable documents (TASK-SKRIPT-39-06-03/07).

Positions are zero-based insertion indexes: top-level units for a new parent,
and children for additions. Existing parents are indivisible top-level units.
"""

from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_ordering import (
    ordering_inside_parent_error,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import NativeExamParent
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error


def _next_id(prefix: str, used: set[str], limit: int) -> str:
    for number in range(1, limit + 1):
        candidate = f"{prefix}_{number:03d}"
        if candidate not in used:
            return candidate
    raise validation_error("Dokumentet har inga lediga identifierare.", details={"kind": prefix})


def _position(position: int, length: int) -> None:
    if not 0 <= position <= length:
        raise validation_error("Positionen finns inte.", details={"position": position})


def _parent(document: NativeExamDocument, parent_id: str) -> NativeExamParent:
    for parent in document.parents:
        if parent.parent_id == parent_id:
            return parent
    raise DomainError(
        code=ErrorCode.NOT_FOUND, message="Uppgiften finns inte.", details={"parent_id": parent_id}
    )


def _new_child(document: NativeExamDocument, child: NativeExamItem) -> NativeExamItem:
    if child.kind is NativeExamItemKind.ORDERING:
        raise ordering_inside_parent_error(child.item_id)
    data = child.model_dump()
    data["item_id"] = _next_id("item", {item.item_id for item in document.items}, 9999)
    data["review"]["parse_origin"] = "teacher_created"
    return NativeExamItem.model_validate(data)


def _rebuild(
    document: NativeExamDocument,
    items: list[NativeExamItem],
    parents: tuple[NativeExamParent, ...],
) -> NativeExamDocument:
    data = document.model_dump()
    data["items"] = [dict(item.model_dump(), sequence=index) for index, item in enumerate(items, 1)]
    data["parents"] = [parent.model_dump() for parent in parents]
    surviving_ids = {item.item_id for item in items}
    data["header"]["tags"] = [
        dict(
            tag.model_dump(),
            question_ids=tuple(value for value in tag.question_ids if value in surviving_ids),
        )
        for tag in document.header.tags
    ]
    # Remove only assets that no surviving item, source or shared instruction uses.
    referenced = {
        asset_id
        for item in items
        for asset_id in (*item.body_asset_ids(), *item.source_asset_ids())
    }
    for body in (document.instructions, *(parent.instruction for parent in parents)):
        referenced.update(
            segment.asset_id
            for paragraph in body
            for segment in paragraph.segments
            if isinstance(segment, NativeAssetSegment)
        )
    data["assets"] = [
        asset.model_dump() for asset in document.assets if asset.asset_id in referenced
    ]
    try:
        return NativeExamDocument.model_validate(data)
    except ValidationError as exc:
        raise validation_error(
            "Ändringen ger ett ogiltigt provdokument.", details={"reason": str(exc)}
        ) from exc


def create_parent(
    document: NativeExamDocument,
    *,
    instruction: tuple[NativeParagraph, ...],
    child: NativeExamItem,
    position: int,
) -> NativeExamDocument:
    starts = [
        index
        for index, item in enumerate(document.items)
        if (parent := document.parent_of(item.item_id)) is None
        or parent.item_ids[0] == item.item_id
    ]
    _position(position, len(starts))
    offset = starts[position] if position < len(starts) else len(document.items)
    new_child = _new_child(document, child)
    try:
        parent = NativeExamParent(
            parent_id=_next_id("parent", {parent.parent_id for parent in document.parents}, 999),
            instruction=instruction,
            item_ids=(new_child.item_id,),
        )
    except ValidationError as exc:
        raise validation_error("Uppgiftens instruktion är ogiltig.") from exc
    items = list(document.items)
    items.insert(offset, new_child)
    parents = tuple(
        sorted(
            (*document.parents, parent),
            key=lambda entry: next(
                i for i, item in enumerate(items) if item.item_id == entry.item_ids[0]
            ),
        )
    )
    return _rebuild(document, items, parents)


def add_child(
    document: NativeExamDocument,
    *,
    parent_id: str,
    child: NativeExamItem,
    position: int,
) -> NativeExamDocument:
    parent = _parent(document, parent_id)
    _position(position, len(parent.item_ids))
    new_child = _new_child(document, child)
    offset = document.item_by_id(parent.item_ids[0]).sequence - 1 + position
    items = list(document.items)
    items.insert(offset, new_child)
    ids = list(parent.item_ids)
    ids.insert(position, new_child.item_id)
    updated = NativeExamParent.model_validate(dict(parent.model_dump(), item_ids=tuple(ids)))
    return _rebuild(document, items, tuple(updated if p == parent else p for p in document.parents))


def delete_parent(
    document: NativeExamDocument,
    *,
    parent_id: str,
) -> NativeExamDocument:
    """Remove the shared instruction, leaving every child in place as a standalone."""
    _parent(document, parent_id)
    return _rebuild(
        document,
        list(document.items),
        tuple(parent for parent in document.parents if parent.parent_id != parent_id),
    )


def delete_parent_with_children(
    document: NativeExamDocument,
    *,
    parent_id: str,
) -> NativeExamDocument:
    """Remove the instruction and exactly the items it owns."""
    parent = _parent(document, parent_id)
    child_ids = set(parent.item_ids)
    if len(child_ids) == len(document.items):
        raise validation_error(
            "Provet måste ha minst en fråga.",
            details={"reason": "exam_requires_question", "parent_id": parent_id},
        )
    return _rebuild(
        document,
        [item for item in document.items if item.item_id not in child_ids],
        tuple(parent for parent in document.parents if parent.parent_id != parent_id),
    )


def delete_child(
    document: NativeExamDocument,
    *,
    parent_id: str,
    item_id: str,
) -> NativeExamDocument:
    parent = _parent(document, parent_id)
    if item_id not in parent.item_ids:
        raise DomainError(
            code=ErrorCode.NOT_FOUND,
            message="Deluppgiften finns inte.",
            details={"parent_id": parent_id, "item_id": item_id},
        )
    if len(parent.item_ids) == 1:
        return delete_parent_with_children(document, parent_id=parent_id)
    updated = NativeExamParent.model_validate(
        dict(
            parent.model_dump(),
            item_ids=tuple(value for value in parent.item_ids if value != item_id),
        )
    )
    return _rebuild(
        document,
        [item for item in document.items if item.item_id != item_id],
        tuple(updated if p == parent else p for p in document.parents),
    )


def reorder_children(
    document: NativeExamDocument,
    *,
    parent_id: str,
    item_ids: tuple[str, ...],
) -> NativeExamDocument:
    parent = _parent(document, parent_id)
    if len(item_ids) != len(parent.item_ids) or set(item_ids) != set(parent.item_ids):
        raise validation_error(
            "Ordningen måste innehålla varje deluppgift exakt en gång.",
            details={"parent_id": parent_id},
        )
    start = document.item_by_id(parent.item_ids[0]).sequence - 1
    items = list(document.items)
    items[start : start + len(item_ids)] = [document.item_by_id(item_id) for item_id in item_ids]
    updated = NativeExamParent.model_validate(dict(parent.model_dump(), item_ids=item_ids))
    return _rebuild(document, items, tuple(updated if p == parent else p for p in document.parents))
