"""Admit one schema-valid batch response into the build state (TASK-SKRIPT-39-05-04).

The strict output schema is the only gate on model output: it limits every anchor to the
batch's own chunks and every kind to the batch's kinds. Admission never rejects or retries
a schema-valid response. A chunk two entries name stays with the first; the later entry
keeps its other chunks. A question the native contract cannot hold, a question the model
marks for review, and every chunk no entry names become review items that keep their
source text. Building one question's item never fails the batch: an item that cannot be
built becomes a review item holding that question's own source text. A question reported
as a type conflict leaves the batch for the pipeline to resend with the kind the source
shows, once: in the resend it is kept as converted.
"""

from collections.abc import Callable

from pydantic import JsonValue, ValidationError

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
    TypeConflict,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import (
    native_item,
    review_source_item,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedItem,
    ProducedMetadata,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    definition_context,
    title_without_answer_key,
    with_accepted_forms,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamItem
from skriptoteket.domain.errors import DomainError

CONFLICT_WITHOUT_KIND_REASON = (
    "AI-tolkningen angav att frågan har en annan svarstyp men inte vilken. "
    "Kontrollera frågan manuellt."
)


def validation_detail(error: ValidationError) -> str:
    """Field locations, error types and the invariant a validator names; never the input."""
    return "; ".join(
        f"{'.'.join(str(part) for part in entry['loc'])}: "
        + (entry["msg"] if entry["type"] == "value_error" else entry["type"])
        for entry in error.errors()
    )


def _printed(anchors: tuple[str, ...], state: DocxBuildState, reason: str) -> NativeExamItem:
    """The question's own chunks as printed, facit included, as one review item."""
    owned = set(anchors)
    return review_source_item(tuple(c for c in state.chunks if c.anchor in owned), reason)


def _source_review(
    index: int, anchors: tuple[str, ...], state: DocxBuildState, code: str, detail: str
) -> NativeExamItem:
    """The question's own source text as a review item, whatever the model wrote."""
    state.record("admission", code, item=index, anchors=anchors, detail=detail)
    return _printed(anchors, state, f"Frågan följer inte provformatet ({detail}).")


def _built(
    index: int, anchors: tuple[str, ...], state: DocxBuildState, build: Callable[[], NativeExamItem]
) -> NativeExamItem:
    """The item ``build`` makes, or its source review item when the item cannot be built."""
    try:
        return build()
    except ValidationError as error:
        return _source_review(
            index, anchors, state, "native_contract_invalid", validation_detail(error)
        )
    except Exception as error:
        # Model output that breaks an assumption of the item builder affects only its question.
        return _source_review(index, anchors, state, "item_unbuildable", type(error).__name__)


def _free(anchors: tuple[str, ...], state: DocxBuildState, seen: set[str]) -> tuple[str, ...]:
    """The anchors no earlier entry of this batch or an earlier batch already holds."""
    return tuple(
        dict.fromkeys(
            a for a in anchors if a not in seen and a not in state.claimed and a in state.owned
        )
    )


def _admit_keys(raw: JsonValue, state: DocxBuildState, seen: set[str]) -> None:
    listed = tuple(a for a in raw if isinstance(a, str)) if isinstance(raw, list) else ()
    for anchor in _free(listed, state, seen):
        state.key_anchors.add(anchor)
        seen.add(anchor)


def _admit_metadata(raw: JsonValue, field_name: str, state: DocxBuildState, seen: set[str]) -> None:
    try:
        metadata = ProducedMetadata.model_validate(raw)
    except ValidationError as error:
        state.record("admission", f"{field_name}_unparsed", detail=validation_detail(error))
        return
    anchors = _free(metadata.source_anchors, state, seen)
    if not anchors:
        state.record("admission", "anchor_conflict", anchors=metadata.source_anchors)
        return
    metadata = metadata.model_copy(update={"source_anchors": anchors})
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


def _admit_item(index: int, raw: JsonValue, state: DocxBuildState, seen: set[str]) -> None:
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
        item = _source_review(index, anchors, state, "item_unparsed", detail)
        state.accepted.append((item, anchors))
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
            state.accepted.append((_printed(anchors, state, CONFLICT_WITHOUT_KIND_REASON), anchors))
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
        state.accepted.append((_printed(anchors, state, reason), anchors))
        return
    instructions = (
        *(a for m in state.instructions for a in m.source_anchors),
        *state.context_anchors,
    )

    def build() -> NativeExamItem:
        context = definition_context(state.chunks, anchors, instructions)
        return native_item(with_accepted_forms(produced, context))

    state.accepted.append((_built(index, anchors, state, build), anchors))


def admit_batch(content: dict[str, JsonValue], state: DocxBuildState) -> None:
    """Admit every entry once; chunks no entry names become review items."""
    seen: set[str] = set()
    _admit_keys(content.get("answer_key_anchors"), state, seen)
    if content.get("title"):
        _admit_metadata(content["title"], "title", state, seen)
    raw_instructions = content.get("instructions")
    for raw in raw_instructions if isinstance(raw_instructions, list) else ():
        _admit_metadata(raw, "instructions", state, seen)
    raw_items = content.get("items")
    for index, raw in enumerate(raw_items if isinstance(raw_items, list) else ()):
        _admit_item(index, raw, state, seen)
    conflicted = {a for conflict in state.conflicts for a in conflict.anchors}
    state.claimed.update(seen - conflicted)
    unnamed = tuple(
        c.anchor for c in state.pending if c.anchor not in conflicted | state.reasons.keys()
    )
    if unnamed:
        state.record("admission", "chunk_unclaimed", anchors=unnamed)
