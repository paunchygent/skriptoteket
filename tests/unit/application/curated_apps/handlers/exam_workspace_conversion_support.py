"""Provisional conversion documents numbered the way the DOCX pipeline numbers them."""

from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
    NativeItemReview,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.protocols.docx_conversion_progress import ConversionUpdate

DOCUMENT_ID = UUID("00000000-0000-4000-8000-000000000001")
PLACEHOLDER_REASON = "Frågan konverteras fortfarande."


def body(text: str) -> tuple[NativeParagraph, ...]:
    return (
        NativeParagraph(heading_level=None, segments=(NativeTextSegment(text=text, marks=()),)),
    )


def placeholder(anchor: str, text: str) -> NativeExamItem:
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.FREE_TEXT,
        body=body(text),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_REQUIRED,
            parse_origin=NativeParseOrigin.SOURCE_FALLBACK,
            reasons=(PLACEHOLDER_REASON,),
        ),
        source_anchor=anchor,
    )


def choice(anchor: str, text: str) -> NativeExamItem:
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.SINGLE_CHOICE,
        body=body(text),
        points=1,
        choices=(
            NativeChoice(choice_id="choice_001", body=body("Ja")),
            NativeChoice(choice_id="choice_002", body=body("Nej")),
        ),
        answer_key=NativeAnswerKey(
            origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED, correct_choice_ids=("choice_001",)
        ),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_COMPLETE, parse_origin=NativeParseOrigin.LLM_PARSED
        ),
        source_anchor=anchor,
    )


def conversion_update(
    units: list[tuple[str, list[NativeExamItem]]],
    *,
    pending: tuple[str, ...],
    title: str = "Prov",
    parents: tuple[tuple[str, tuple[str, ...]], ...] = (),
    extras: tuple[NativeExamItem, ...] = (),
    document_id: UUID = DOCUMENT_ID,
) -> ConversionUpdate:
    """Number items the way the pipeline does: item_001.. in document order."""
    items: list[NativeExamItem] = []
    item_ids: dict[str, tuple[str, ...]] = {}
    extra_ids: list[str] = []
    for question_id, unit_items in units:
        ids = []
        for item in unit_items:
            item_id = f"item_{len(items) + 1:03d}"
            items.append(item.model_copy(update={"item_id": item_id, "sequence": len(items) + 1}))
            ids.append(item_id)
        item_ids[question_id] = tuple(ids)
    for item in extras:
        item_id = f"item_{len(items) + 1:03d}"
        items.append(item.model_copy(update={"item_id": item_id, "sequence": len(items) + 1}))
        extra_ids.append(item_id)
    by_source = {question_id: ids for question_id, ids in item_ids.items()}
    document = NativeExamDocument(
        document_id=document_id,
        revision=1,
        title=title,
        items=tuple(items),
        parents=tuple(
            NativeExamParent(
                parent_id=f"parent_{index:03d}",
                instruction=body("Välj rätt svar."),
                item_ids=tuple(i for q in questions for i in by_source[q]),
            )
            for index, (_, questions) in enumerate(parents, start=1)
        ),
        origin=NativeExamDocumentOrigin(
            kind="docx_import", source_filename="prov.docx", source_sha256="a" * 64
        ),
    )
    return ConversionUpdate(
        filled=tuple(q for q, _ in units if q not in pending),
        pending=pending,
        document=document,
        item_ids=item_ids,
        extra_item_ids=tuple(extra_ids),
        parent_ids={},
    )
