"""Assemble type batches into one document in source order (TASK-SKRIPT-39-05-04 step 3).

Each finished batch merges into one document-wide state, because the opening heading,
section totals and section-instruction parents are document-wide. A provisional
document shows every question still converting as a placeholder with its source text;
the final document turns every chunk no batch converted into a review item. Both map
every grouped question to its items, and the check reports any question that is not
exactly one converted item or its review items, and any governing instruction whose
same-kind questions do not share a parent.
"""

from __future__ import annotations

from collections.abc import Mapping

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    NO_ITEM_REASON,
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import assemble_build_result
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildEvent,
    DocxBuildResult,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import QuestionFamily
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import ExamManifest
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeExamDocument,
    NativeExamItem,
    NativeExamItemKind,
    NativeItemReview,
    NativeItemReviewState,
    NativeParagraph,
    NativeParseOrigin,
    NativeTextSegment,
)
from skriptoteket.protocols.docx_conversion_progress import ConversionUpdate

PLACEHOLDER_REASON = "Frågan konverteras fortfarande."


def merge_batch(
    target: DocxBuildState, batch: DocxBuildState, title_anchors: frozenset[str]
) -> None:
    """Fold one finished batch into the document-wide state.

    The exam title comes only from the chunks the grouping names as the title, whichever
    batch finishes first; a title another batch reports is kept as an instruction.
    """
    target.accepted.extend(batch.accepted)
    title = batch.title
    if (
        title is not None
        and target.title is None
        and title_anchors.issuperset(title.source_anchors)
    ):
        target.title = title
        title = None
    target.instructions = (
        *target.instructions,
        *((title,) if title is not None else ()),
        *batch.instructions,
    )
    target.key_anchors |= batch.key_anchors
    target.claimed |= batch.claimed
    target.reasons.update(
        (anchor, reason) for anchor, reason in batch.reasons.items() if anchor not in batch.claimed
    )
    target.events.extend(batch.events)
    for mine, theirs, complete in (
        ("input_tokens", batch.input_tokens, batch.input_complete),
        ("output_tokens", batch.output_tokens, batch.output_complete),
    ):
        if theirs is not None:
            setattr(target, mine, (getattr(target, mine) or 0) + theirs)
        if not complete:
            setattr(target, f"{mine.split('_')[0]}_complete", False)


def with_confidence(
    state: DocxBuildState, families: tuple[QuestionFamily, ...], confidence: Mapping[str, float]
) -> None:
    """Record the first-pass probability of the converted label on each converted item."""
    owner = {a: f.question_id for f in families for a in f.question_anchors}
    updated = []
    for item, anchors in state.accepted:
        qid = next((owner[a] for a in anchors if a in owner), None)
        if qid is not None and qid in confidence:
            review = item.review.model_copy(update={"confidence": confidence[qid]})
            item = item.model_copy(update={"review": review})
        updated.append((item, anchors))
    state.accepted = updated


def placeholder_item(state: DocxBuildState, family: QuestionFamily) -> NativeExamItem:
    """A converting question shows its own source text until its batch fills it."""
    texts = [state.chunk_by_anchor[a].text for a in family.question_anchors]
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.FREE_TEXT,
        body=tuple(
            NativeParagraph(segments=(NativeTextSegment(text=text),)) for text in texts if text
        )
        or (NativeParagraph(segments=(NativeTextSegment(text="Tomt källstycke."),)),),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_REQUIRED,
            parse_origin=NativeParseOrigin.DETERMINISTIC,
            reasons=(PLACEHOLDER_REASON,),
        ),
        source_anchor=family.question_anchors[0],
    )


def provisional_result(
    state: DocxBuildState, families: tuple[QuestionFamily, ...], pending: frozenset[str]
) -> DocxBuildResult:
    """Converted batches plus one placeholder per pending question; nothing else is shown."""
    placeholders = [
        (placeholder_item(state, family), family.question_anchors)
        for family in families
        if family.question_id in pending
    ]
    finished = frozenset(
        a for family in families if family.question_id not in pending for a in family.claims
    )
    return assemble_build_result(
        document_id=state.document_id,
        filename=state.filename,
        source_sha256=state.source_sha256,
        chunks=state.chunks,
        accepted=(*state.accepted, *placeholders),
        review_reasons={
            chunk.anchor: state.reasons.get(chunk.anchor, NO_ITEM_REASON)
            for chunk in state.chunks
            if chunk.anchor in finished and chunk.anchor not in state.claimed
        },
        key_anchors=frozenset(state.key_anchors),
        title=state.title,
        instructions=state.instructions,
    )


def conversion_update(
    document: NativeExamDocument,
    families: tuple[QuestionFamily, ...],
    filled: tuple[str, ...],
    pending: tuple[str, ...],
) -> ConversionUpdate:
    """Map every grouped question to its items and the parent it sits under."""
    owner = {a: f.question_id for f in families for a in f.claims}
    item_ids: dict[str, list[str]] = {f.question_id: [] for f in families}
    extra: list[str] = []
    for item in document.items:
        qid = owner.get(item.source_anchor or "")
        (item_ids[qid] if qid is not None else extra).append(item.item_id)
    parents = {item_id: p.parent_id for p in document.parents for item_id in p.item_ids}
    parent_ids = {
        qid: parents[ids[0]] for qid, ids in item_ids.items() if ids and ids[0] in parents
    }
    return ConversionUpdate(
        filled=filled,
        pending=pending,
        document=document,
        item_ids={qid: tuple(ids) for qid, ids in item_ids.items()},
        extra_item_ids=tuple(extra),
        parent_ids=parent_ids,
    )


def assembly_check(
    document: NativeExamDocument,
    manifest: ExamManifest,
    families: tuple[QuestionFamily, ...],
    update: ConversionUpdate,
) -> tuple[DocxBuildEvent, ...]:
    """Report questions not converted exactly once and governed runs without their parent."""
    events: list[DocxBuildEvent] = []
    items = {item.item_id: item for item in document.items}
    for family in families:
        ids = update.item_ids[family.question_id]
        converted = [i for i in ids if items[i].review.parse_origin is NativeParseOrigin.LLM_PARSED]
        if not ids or len(converted) > 1:
            events.append(
                DocxBuildEvent(
                    stage="assembly",
                    code="question_not_once",
                    anchors=family.question_anchors[:1],
                    detail=f"{family.question_id}: {len(ids)} items",
                )
            )
    for context in manifest.contexts:
        governed = [q for q in context.governs if update.item_ids.get(q)]
        kinds = {items[update.item_ids[q][0]].kind for q in governed}
        parents = {update.parent_ids.get(q) for q in governed}
        if len(governed) >= 2 and len(kinds) == 1 and (None in parents or len(parents) > 1):
            events.append(
                DocxBuildEvent(
                    stage="assembly",
                    code="parent_differs_from_grouping",
                    anchors=(context.anchor,),
                    detail=f"governs {', '.join(governed)}",
                )
            )
    return tuple(events)
