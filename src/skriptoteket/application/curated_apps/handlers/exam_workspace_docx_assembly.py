"""Assemble type batches into one document in source order (TASK-SKRIPT-39-05-04 step 3).

Each finished batch merges into one document-wide state, because the opening heading,
section totals and section-instruction parents are document-wide. A provisional
document shows every question still converting as a placeholder with its source text;
the final document turns every chunk no batch converted into a review item. Both map
every grouped question to its items, and the check reports any question that is not
exactly one converted item or its review items, and any governing instruction whose
questions, of whatever kinds, do not share a parent.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from types import MappingProxyType

from pydantic import ValidationError

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_admit_metadata import (
    validation_detail,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    NO_ITEM_REASON,
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import (
    assemble_build_result,
    review_source_item,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildEvent,
    DocxBuildResult,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import QuestionFamily
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    ExamManifest,
    SharedContext,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_lines import printed_points_plan
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeParseOrigin,
)
from skriptoteket.protocols.docx_conversion_progress import ConversionUpdate
from skriptoteket.protocols.item_type_labeler import ACCEPT_THRESHOLD

PLACEHOLDER_REASON = "Frågan konverteras fortfarande."
_BELOW_ACCEPT = math.nextafter(ACCEPT_THRESHOLD, 0.0)


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
    # A new mapping: a trial snapshot shares the run state's mapping until it is replaced.
    target.owned_contexts = {**target.owned_contexts, **batch.owned_contexts}
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


def with_type_check_mark(state: DocxBuildState) -> None:
    """Mark each item kept after a repeated type conflict for a type check (D7).

    Its confidence stays below the acceptance threshold; no other item carries a confidence,
    because the first-pass label probability says nothing once conversion settles the type.
    """
    updated = []
    for item, anchors in state.accepted:
        if state.kept_conflicts.intersection(anchors):
            review = item.review.model_copy(update={"confidence": _BELOW_ACCEPT})
            item = item.model_copy(update={"review": review})
        updated.append((item, anchors))
    state.accepted = updated


def validated(state: DocxBuildState) -> None:
    """Check every admitted item against the native contract again, because later updates
    copy items without validation; an item that fails holds its whole question's source text
    for review."""
    checked = []
    for item, anchors in state.accepted:
        try:
            item = NativeExamItem.model_validate(item.model_dump())
        except ValidationError as error:
            detail = validation_detail(error)
            state.record("admission", "native_contract_invalid", anchors=anchors, detail=detail)
            reason = f"Frågan följer inte provformatet ({detail})."
            item, anchors = state.printed(anchors, reason, state.claimed)
        checked.append((item, anchors))
    state.accepted = checked


def placeholder_item(state: DocxBuildState, family: QuestionFamily) -> NativeExamItem:
    """A converting question shows its own source text and pictures until its batch fills it.

    The placeholder is one review item over the question's own chunks, so a picture keeps
    its exact place while the converter runs and the question stays locked for the teacher.
    """
    return review_source_item(
        tuple(
            state.chunk_by_anchor[anchor]
            for anchor in family.question_anchors
            if anchor not in state.header_anchors
        ),
        PLACEHOLDER_REASON,
    )


def exam_metadata_anchors(contexts: tuple[SharedContext, ...]) -> frozenset[str]:
    """The anchors of exam-metadata contexts (Namn, Klass, Datum): never item text."""
    return frozenset(c.anchor for c in contexts if c.scope == "exam_metadata")


def exam_wide_anchors(
    contexts: tuple[SharedContext, ...], families: tuple[QuestionFamily, ...]
) -> frozenset[str]:
    """Anchors of exam-owned contexts that govern every question or none, plus every metadata
    anchor.

    An exam-owned context that governs no question is exam-wide text: it belongs to the
    document's instructions, never to a section parent's heading run or instruction.
    """
    every = {family.question_id for family in families}
    return exam_metadata_anchors(contexts) | frozenset(
        c.anchor
        for c in contexts
        if c.owner == "exam" and (not c.governs or every <= set(c.governs))
    )


def question_owned_contexts(
    contexts: tuple[SharedContext, ...], families: tuple[QuestionFamily, ...]
) -> dict[str, tuple[str, ...]]:
    """Each question's own anchor, mapped to the contexts that question owns, in manifest order.

    A context a question owns joins that question's item, or its source-review item, when no
    reply entry holds it (ruling 2026-10-18 c). A context governing two or more questions is
    its section parent's instruction (D40), so no single question owns it here.
    """
    governed = governed_anchors(contexts, families)
    owned = {
        family.question_id: tuple(
            c.anchor for c in contexts if c.owner == family.question_id and c.anchor not in governed
        )
        for family in families
    }
    return {
        anchor: owned[family.question_id]
        for family in families
        if owned[family.question_id]
        for anchor in family.question_anchors
    }


def governed_anchors(
    contexts: tuple[SharedContext, ...], families: tuple[QuestionFamily, ...]
) -> dict[str, frozenset[str]]:
    """Each shared context that governs two or more questions, with every anchor they own.

    Exam-wide text and exam metadata govern nothing: they belong to the document.
    """
    claims = {family.question_id: family.claims for family in families}
    exam_wide = exam_wide_anchors(contexts, families)
    return {
        context.anchor: frozenset().union(*(claims[q] for q in context.governs if q in claims))
        for context in contexts
        if len(context.governs) >= 2 and context.anchor not in exam_wide
    }


def provisional_result(
    state: DocxBuildState,
    families: tuple[QuestionFamily, ...],
    pending: frozenset[str],
    governed: Mapping[str, frozenset[str]],
    exam_wide: frozenset[str] = frozenset(),
    exam_metadata: frozenset[str] = frozenset(),
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
    questions = tuple(family.question_anchors for family in families)
    heading_instructions = state.heading_instructions
    heading_anchors = {
        a for instruction in heading_instructions for a in instruction.source_anchors
    }
    return assemble_build_result(
        document_id=state.document_id,
        filename=state.filename,
        source_sha256=state.source_sha256,
        chunks=tuple(c for c in state.chunks if c.anchor not in state.header_anchors),
        accepted=(*state.accepted, *placeholders),
        review_reasons={
            chunk.anchor: state.reasons.get(chunk.anchor, NO_ITEM_REASON)
            for chunk in state.chunks
            if chunk.anchor in finished
            and chunk.anchor not in state.claimed
            and chunk.anchor not in state.header_anchors
            and chunk.anchor not in heading_anchors
        },
        key_anchors=frozenset(state.key_anchors),
        title=state.title,
        instructions=(*state.instructions, *heading_instructions),
        governed=governed,
        exam_wide=exam_wide,
        exam_metadata=exam_metadata,
        questions=questions,
        printed=printed_points_plan(state.chunks, questions),
    )


def conversion_update(
    document: NativeExamDocument,
    families: tuple[QuestionFamily, ...],
    filled: tuple[str, ...],
    pending: tuple[str, ...],
    *,
    assets_by_id: Mapping[str, bytes] = MappingProxyType({}),
) -> ConversionUpdate:
    """Map every grouped question to its items, the parent it sits under, and its pictures."""
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
        assets_by_id=assets_by_id,
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
        parents = {update.parent_ids.get(q) for q in governed}
        if len(governed) >= 2 and (None in parents or len(parents) > 1):
            events.append(
                DocxBuildEvent(
                    stage="assembly",
                    code="parent_differs_from_grouping",
                    anchors=(context.anchor,),
                    detail=f"governs {', '.join(governed)}",
                )
            )
    return tuple(events)
