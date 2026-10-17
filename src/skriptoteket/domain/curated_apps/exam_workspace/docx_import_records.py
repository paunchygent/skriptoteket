"""Project source wording and per-question import decisions, never raw build events."""

from __future__ import annotations

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import DocxBuildEvent
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_import_record import (
    NativeExamAnswerKeyStep,
    NativeExamChosenTypeStep,
    NativeExamImportRecord,
    NativeExamImportStep,
    NativeExamOriginalWording,
    NativeExamRetryStep,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
    NativeParseOrigin,
)


def with_docx_import_records(
    document: NativeExamDocument,
    *,
    chunks: tuple[DocxChunk, ...],
    events: tuple[DocxBuildEvent, ...],
) -> NativeExamDocument:
    """Join only a question's own plain chunks; key/shared chunks never enter its prompt.

    Ungrouped fallback items each correspond to their exact source anchor. A conflict
    event identifies the resend's requested kind; a kept conflict is not another resend.
    """
    by_anchor = {chunk.anchor: chunk for chunk in chunks}
    items: list[NativeExamItem] = []
    for item in document.items:
        source = item.retry_source
        own = (
            source.chunks
            if source is not None
            else ((by_anchor[item.source_anchor],) if item.source_anchor in by_anchor else ())
        )
        steps: list[NativeExamImportStep] = [
            NativeExamChosenTypeStep(chosen_kind=item.kind),
            NativeExamAnswerKeyStep(origin=item.answer_key.origin),
        ]
        if source is not None:
            anchors = {chunk.anchor for chunk in source.chunks}
            conflict = next(
                (
                    event
                    for event in events
                    if event.stage == "admission"
                    and event.code == "type_conflict"
                    and anchors.intersection(event.anchors)
                ),
                None,
            )
            if conflict is not None:
                chosen = NativeExamItemKind(conflict.detail)
                if chosen != source.label_kind:
                    steps.append(
                        NativeExamRetryStep(
                            reason="type_conflict",
                            from_kind=source.label_kind,
                            chosen_kind=chosen,
                            outcome=(
                                "converted"
                                if item.review.parse_origin is NativeParseOrigin.LLM_PARSED
                                else "review_required"
                            ),
                        )
                    )
        record = NativeExamImportRecord(
            original_wording=NativeExamOriginalWording(
                question_text="\n".join(chunk.text for chunk in own),
                answer_key_text=item.facit_text,
            ),
            steps=tuple(steps),
        )
        items.append(item.model_copy(update={"import_record": record}))
    return document.model_copy(update={"items": tuple(items)})
