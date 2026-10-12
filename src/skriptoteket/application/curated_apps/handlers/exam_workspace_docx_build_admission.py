"""Admit one schema-valid batch response into the build state (TASK-SKRIPT-39-05-04).

The strict output schema is the only gate on model output: it limits every anchor to the
batch's own chunks and every kind to the batch's kinds. Admission never rejects or retries
a schema-valid response. A chunk two entries name stays with the first; the later entry
keeps its other chunks. A question the native contract cannot hold, a question the model
marks for review, and every chunk no entry names become review items that keep their
source text; a question's review item shows all its own chunks as printed. A chunk the
grouping gives a question as its own stays with the item that lists it, also when the reply
lists it as an answer key, and is no answer key when an item lists another chunk of its
question. It is never a title or instruction, whatever the reply lists. A converted item that
leaves out own chunks of its question holds them under a check mark that shows them as printed
(D41). Building one question's item never fails the batch: an
item that cannot be built becomes a review item holding that question's own source text. A
question reported as a type conflict leaves the batch for the pipeline to resend with the kind
the source shows, once: in the resend it is kept as converted.
"""

from collections.abc import Callable

from pydantic import JsonValue, ValidationError

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
    TypeConflict,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedItem,
    ProducedMetadata,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    definition_context,
    title_without_answer_key,
    with_accepted_forms,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItem,
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.domain.errors import DomainError

CONFLICT_WITHOUT_KIND_REASON = (
    "AI-tolkningen angav att frågan har en annan svarstyp men inte vilken. "
    "Kontrollera frågan manuellt."
)
LEFT_OUT_REASON = (
    "Delar av källtexten saknas i den konverterade frågan – kontrollera mot källan. "
    "Källtext som saknas:"
)
DRAWING_SHOWN = "[Bild utan text]"


def validation_detail(error: ValidationError) -> str:
    """Field locations, error types and the invariant a validator names; never the input."""
    return "; ".join(
        f"{'.'.join(str(part) for part in entry['loc'])}: "
        + (entry["msg"] if entry["type"] == "value_error" else entry["type"])
        for entry in error.errors()
    )


Admitted = tuple[NativeExamItem, tuple[str, ...]]


def _source_review(
    index: int,
    anchors: tuple[str, ...],
    state: DocxBuildState,
    seen: set[str],
    code: str,
    detail: str,
) -> Admitted:
    """The whole question's source text as a review item, whatever the model wrote."""
    state.record("admission", code, item=index, anchors=anchors, detail=detail)
    return state.printed(anchors, f"Frågan följer inte provformatet ({detail}).", seen)


def _built(
    index: int,
    anchors: tuple[str, ...],
    state: DocxBuildState,
    seen: set[str],
    build: Callable[[], NativeExamItem],
) -> Admitted:
    """The item ``build`` makes, or its source review item when the item cannot be built."""
    try:
        return build(), anchors
    except ValidationError as error:
        return _source_review(
            index, anchors, state, seen, "native_contract_invalid", validation_detail(error)
        )
    except Exception as error:
        # Model output that breaks an assumption of the item builder affects only its question.
        return _source_review(index, anchors, state, seen, "item_unbuildable", type(error).__name__)


def _free(anchors: tuple[str, ...], state: DocxBuildState, seen: set[str]) -> tuple[str, ...]:
    """The anchors no earlier entry of this batch or an earlier batch already holds."""
    return tuple(
        dict.fromkeys(
            a for a in anchors if a not in seen and a not in state.claimed and a in state.owned
        )
    )


def _admit_keys(
    raw: JsonValue, state: DocxBuildState, seen: set[str], item_held: frozenset[str]
) -> None:
    listed = tuple(a for a in raw if isinstance(a, str)) if isinstance(raw, list) else ()
    for anchor in _free(listed, state, seen):
        if item_held.intersection(state.question_by_anchor.get(anchor, ())):
            continue
        state.key_anchors.add(anchor)
        seen.add(anchor)


def _admit_metadata(raw: JsonValue, field_name: str, state: DocxBuildState, seen: set[str]) -> None:
    try:
        metadata = ProducedMetadata.model_validate(raw)
    except ValidationError as error:
        state.record("admission", f"{field_name}_unparsed", detail=validation_detail(error))
        return
    listed = _free(metadata.source_anchors, state, seen)
    # The grouping decides ownership: a question's own chunk stays with its question (D41).
    own = tuple(a for a in listed if a in state.question_by_anchor and a not in state.governing)
    if own:
        state.record("admission", f"{field_name}_own_chunk", anchors=own)
    anchors = tuple(a for a in listed if a not in own)
    if not anchors:
        if not own:
            state.record("admission", "anchor_conflict", anchors=metadata.source_anchors)
        return
    # The reply's text may hold the withheld chunks' wording, so the rest shows its source text.
    text = "\n".join(state.chunk_by_anchor[a].text for a in anchors) if own else metadata.text
    metadata = metadata.model_copy(update={"text": text, "source_anchors": anchors})
    if field_name == "title" and state.title is None:
        try:
            text = title_without_answer_key(metadata.text)
        except DomainError as error:
            # A title of answer-key wording alone names no title; its chunks stay unclaimed.
            state.record("admission", "title_unparsed", anchors=anchors, detail=error.code.value)
            return
        state.title = metadata.model_copy(update={"text": text})
    else:
        state.instructions = (*state.instructions, metadata)
    seen.update(anchors)


def _raw_anchors(raw: JsonValue) -> tuple[str, ...]:
    anchors = raw.get("source_anchors") if isinstance(raw, dict) else None
    return tuple(a for a in anchors if isinstance(a, str)) if isinstance(anchors, list) else ()


def _with_left_out(
    index: int,
    admitted: Admitted,
    state: DocxBuildState,
    seen: set[str],
    item_held: frozenset[str],
) -> Admitted:
    """A converted item that leaves out own chunks of its question holds them under a check
    mark that shows them as printed and blocks export until the teacher handles it (D41).

    A left-out chunk is an own chunk of a question the item touches that no item of the
    reply lists and no entry holds yet.
    """
    item, anchors = admitted
    if item.review.parse_origin is not NativeParseOrigin.LLM_PARSED:
        return admitted
    own = set().union(*(state.question_by_anchor.get(a, ()) for a in anchors))
    left_out = tuple(
        c.anchor
        for c in state.pending
        if c.anchor in own and c.anchor not in item_held and c.anchor not in seen
    )
    if not left_out:
        return admitted
    seen.update(left_out)
    state.record("admission", "own_chunks_left_out", item=index, anchors=left_out)
    chunks = tuple(state.chunk_by_anchor[a] for a in left_out)
    texts = tuple(c.text or DRAWING_SHOWN for c in chunks if c.text or c.kind == "drawing")
    review = item.review.model_copy(
        update={
            "state": NativeItemReviewState.REVIEW_REQUIRED,
            "reasons": (*item.review.reasons, LEFT_OUT_REASON, *texts),
        }
    )
    return item.model_copy(update={"review": review}), (*anchors, *left_out)


def _admit_item(
    index: int, raw: JsonValue, state: DocxBuildState, seen: set[str], item_held: frozenset[str]
) -> None:
    try:
        produced = ProducedItem.model_validate(raw)
    except ValidationError as error:
        # The question the entry names becomes one review item holding its source text.
        anchors = _free(_raw_anchors(raw), state, seen)
        detail = validation_detail(error)
        if not anchors:
            state.record("admission", "item_unparsed", item=index, detail=detail)
            return
        seen.update(anchors)
        state.accepted.append(_source_review(index, anchors, state, seen, "item_unparsed", detail))
        return
    anchors = _free(produced.source_anchors, state, seen)
    if anchors != produced.source_anchors:
        state.record("admission", "anchor_conflict", item=index, anchors=produced.source_anchors)
    if not anchors:
        return
    produced = produced.model_copy(update={"source_anchors": anchors})
    seen.update(anchors)
    if produced.outcome == "type_conflict":
        kind = produced.conflict_kind
        if kind is None or (state.allowed_kinds is not None and kind in state.allowed_kinds):
            state.accepted.append(state.printed(anchors, CONFLICT_WITHOUT_KIND_REASON, seen))
            return
        if not state.keep_conflicts:
            state.conflicts.append(TypeConflict(anchors, kind))
            state.record("admission", "type_conflict", item=index, anchors=anchors, detail=kind)
            return
        # A resent question that conflicts again is kept as converted, as the kind the source
        # shows, with the type-check mark.
        state.record("admission", "type_conflict_kept", item=index, anchors=anchors, detail=kind)
        state.kept_conflicts.update(anchors)
        produced = produced.model_copy(update={"kind": kind})
    if produced.outcome == "review":
        cause = produced.review_reason or "ingen orsak angavs"
        reason = f"AI-tolkningen markerade frågan för granskning: {cause}"
        state.record("admission", "model_review", item=index, anchors=anchors, detail=reason)
        state.accepted.append(state.printed(anchors, reason, seen))
        return
    instructions = (
        *(a for m in state.instructions for a in m.source_anchors),
        *state.context_anchors,
    )

    def build() -> NativeExamItem:
        context = definition_context(state.chunks, anchors, instructions)
        return native_item(with_accepted_forms(produced, context))

    built = _built(index, anchors, state, seen, build)
    state.accepted.append(_with_left_out(index, built, state, seen, item_held))


def admit_batch(content: dict[str, JsonValue], state: DocxBuildState) -> None:
    """Admit every entry once; chunks no entry names become review items."""
    seen: set[str] = set()
    raw_items = content.get("items")
    items = raw_items if isinstance(raw_items, list) else []
    item_held = frozenset(a for raw in items for a in _raw_anchors(raw))
    _admit_keys(content.get("answer_key_anchors"), state, seen, item_held)
    if content.get("title"):
        _admit_metadata(content["title"], "title", state, seen)
    raw_instructions = content.get("instructions")
    for raw in raw_instructions if isinstance(raw_instructions, list) else ():
        _admit_metadata(raw, "instructions", state, seen)
    for index, raw in enumerate(items):
        _admit_item(index, raw, state, seen, item_held)
    conflicted = {a for conflict in state.conflicts for a in conflict.anchors}
    state.claimed.update(seen - conflicted)
    # A governing chunk with text becomes its section parent's instruction (D40).
    unnamed = tuple(
        c.anchor
        for c in state.pending
        if c.anchor not in conflicted | state.reasons.keys()
        and not (c.anchor in state.governing and c.text)
    )
    if unnamed:
        state.record("admission", "chunk_unclaimed", anchors=unnamed)
