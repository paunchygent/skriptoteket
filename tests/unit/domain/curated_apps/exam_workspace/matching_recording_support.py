"""Matching items from the fresh live recordings, with their answer key removed."""

from uuid import uuid4

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from tests.unit.domain.curated_apps.exam_workspace.recorded_native_exam_support import (
    ENGLISH_EXAM,
    recorded_converted_items,
    recorded_exam_language,
)


def recorded_matching_items(
    *, keyed: bool = False, exam: str = ENGLISH_EXAM
) -> tuple[NativeExamItem, ...]:
    """Native matching items of the recording; ``keyed=False`` drops every pair (origin ABSENT)."""

    items: list[NativeExamItem] = []
    for produced in recorded_converted_items(exam):
        if produced.kind is not NativeExamItemKind.MATCHING:
            continue
        if not keyed:
            produced = produced.model_copy(update={"match_pairs": ()})
        item = aligned_native_item(produced, language=recorded_exam_language(exam)).item
        sequence = len(items) + 1
        items.append(
            NativeExamItem.model_validate(
                {**dict(item), "item_id": f"item_{sequence:03d}", "sequence": sequence}
            )
        )
    return tuple(items)


def document_of(*items: NativeExamItem, revision: int = 1) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=revision,
        title="Recorded matching items",
        items=items,
        origin=NativeExamDocumentOrigin(kind="created"),
    )
