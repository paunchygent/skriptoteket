"""Admit produced items through the native contract and chunk-role bookkeeping."""

import json
from collections import Counter

from pydantic import BaseModel, JsonValue, ValidationError

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import (
    native_item,
    review_item,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildEnvelope,
    ProducedItem,
    ProducedMetadata,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    OPENING_HEADING_IS_TITLE,
    definition_context,
    item_rule_violation,
    label_rule_violation,
    opening_heading,
    title_rule_violation,
    with_accepted_forms,
    with_printed_hints,
)

_ENVELOPE_FIELDS = set(DocxBuildEnvelope.model_fields)


class _Rejected(Exception):
    def __init__(self, code: str, detail: str, reason: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.reason = reason


def validation_detail(error: ValidationError) -> str:
    """Field location and message only; the offending input is never included."""
    return "; ".join(
        f"{'.'.join(str(part) for part in entry['loc']) or '<root>'}: {entry['msg']}"
        for entry in error.errors(include_url=False, include_input=False)
    )[:500]


def _parse[T: BaseModel](model: type[T], raw: JsonValue) -> T:
    try:
        return model.model_validate_json(json.dumps(raw), strict=True)
    except ValidationError as error:
        detail = validation_detail(error)
        raise _Rejected(
            "item_schema_invalid", detail, f"Svaret följer inte AI-kontraktet ({detail})."
        ) from error


def _without_key_anchors(produced: ProducedItem, state: DocxBuildState) -> ProducedItem:
    """A chunk already admitted as facit stays facit; the item keeps its other chunks."""
    kept = tuple(a for a in produced.source_anchors if a not in state.key_anchors)
    if not kept or kept == produced.source_anchors:
        return produced
    return produced.model_copy(update={"source_anchors": kept})


def _require_anchors(anchors: tuple[str, ...], state: DocxBuildState, seen: set[str]) -> None:
    unknown = [a for a in anchors if a not in state.known_anchors]
    if unknown:
        detail = f"unknown anchors {unknown}"
        raise _Rejected("anchor_unknown", detail, f"Okända källankare ({detail}).")
    counts = Counter(anchors)
    taken = [a for a in anchors if a in state.claimed or a in state.key_anchors or a in seen] + [
        a for a in anchors if counts[a] > 1
    ]
    if taken:
        detail = f"anchors already used {sorted(set(taken))}"
        raise _Rejected(
            "anchor_conflict", detail, f"Källstycket används redan av annat innehåll ({detail})."
        )


def _admit_keys(raw: JsonValue, state: DocxBuildState) -> None:
    """Facit is decided by position; the opening heading stays pending as the title."""
    anchors = raw if isinstance(raw, list) else []
    valid = [a for a in anchors if isinstance(a, str) and a in state.known_anchors]
    if len(valid) != len(anchors):
        state.record(
            "admission", "answer_key_anchor_unknown", detail=f"{len(anchors) - len(valid)} unknown"
        )
    heading = opening_heading(state.chunks)
    if heading is not None and heading.anchor in valid:
        valid.remove(heading.anchor)
        detail = f"answer_key_anchors {heading.anchor} {OPENING_HEADING_IS_TITLE}"
        state.record("admission", "answer_key_source_rule", anchors=(heading.anchor,))
        state.failures = (*state.failures, detail)
    for anchor in valid:
        if anchor not in state.claimed:
            state.key_anchors.add(anchor)
            state.claimed.add(anchor)


def _require_title_rule(title: ProducedMetadata, state: DocxBuildState) -> None:
    sources = (state.chunk_by_anchor[a] for a in title.source_anchors)
    violation = title_rule_violation(title, sources, opening_heading(state.chunks))
    if violation:
        state.failures = (*state.failures, violation)
        raise _Rejected("source_rule", violation, "Titeln följer inte källans rubrik.")


def _admit_metadata(content: dict[str, JsonValue], state: DocxBuildState, seen: set[str]) -> None:
    raw_title = content["title"]
    raw_instructions = content["instructions"]
    candidates: list[tuple[str, JsonValue]] = [("title", raw_title)] if raw_title else []
    if isinstance(raw_instructions, list):
        candidates.extend(("instructions", value) for value in raw_instructions)
    for field_name, raw in candidates:
        try:
            metadata = _parse(ProducedMetadata, raw)
            _require_anchors(metadata.source_anchors, state, seen)
            if field_name == "title" and state.title is None:
                _require_title_rule(metadata, state)
        except _Rejected as rejected:
            state.record("admission", f"{field_name}_{rejected.code}", detail=rejected.detail)
            continue
        if field_name == "title" and state.title is None:
            state.title = metadata
        else:
            state.instructions = (*state.instructions, metadata)
        seen.update(metadata.source_anchors)


def _admit_item(
    index: int, raw: JsonValue, state: DocxBuildState, seen: set[str], rejected_anchors: set[str]
) -> None:
    anchors: tuple[str, ...] = ()
    try:
        produced = _without_key_anchors(_parse(ProducedItem, raw), state)
        anchors = produced.source_anchors
        _require_anchors(anchors, state, seen)
        own = tuple(state.chunk_by_anchor[a] for a in anchors)
        produced = with_printed_hints(produced, own)
        violation = item_rule_violation(produced, own) or label_rule_violation(produced, own)
        if violation:
            raise _Rejected(
                "source_rule",
                violation,
                "Frågans luckor, svarstyp eller etiketter följer inte källans struktur.",
            )
        try:
            if produced.outcome == "review":
                cause = produced.review_reason or "ingen orsak angavs"
                reason = f"AI-tolkningen markerade frågan för granskning: {cause}"
                item = review_item(produced, reason)
                state.record(
                    "admission", "model_review", item=index, anchors=anchors, detail=reason
                )
            else:
                instructions = (a for m in state.instructions for a in m.source_anchors)
                context = definition_context(state.chunks, anchors, instructions)
                item = native_item(with_accepted_forms(produced, context))
        except ValidationError as error:
            detail = validation_detail(error)
            raise _Rejected(
                "native_contract_invalid", detail, f"Frågan följer inte provformatet ({detail})."
            ) from error
    except _Rejected as rejected:
        state.record(
            "admission", rejected.code, item=index, anchors=anchors, detail=rejected.detail
        )
        state.fail_chunks(anchors, rejected.reason)
        rejected_anchors.update(anchors)
        state.failures = (*state.failures, f"items[{index}] {rejected.code}: {rejected.detail}")
        return
    state.accepted.append((item, anchors))
    seen.update(anchors)


def admit_batch(content: dict[str, JsonValue], state: DocxBuildState) -> None:
    """Freeze converted items; leave failing and unclaimed chunks pending for retry."""
    state.failures = ()
    if set(content) != _ENVELOPE_FIELDS or not isinstance(content["items"], list):
        detail = f"top-level fields {sorted(content)}"
        state.record("admission", "envelope_invalid", detail=detail)
        state.fail_all_pending(f"Svaret följer inte AI-kontraktet ({detail}).")
        state.failures = (f"envelope_invalid: {detail}",)
        return
    seen: set[str] = set()
    rejected_anchors: set[str] = set()
    _admit_keys(content["answer_key_anchors"], state)
    _admit_metadata(content, state, seen)
    for index, raw in enumerate(content["items"]):
        _admit_item(index, raw, state, seen, rejected_anchors)
    state.claimed.update(seen)
    uncovered = tuple(c.anchor for c in state.pending if c.anchor not in rejected_anchors)
    if uncovered:
        state.record("admission", "chunk_unclaimed", anchors=uncovered)
        state.failures = (*state.failures, f"chunks without item or metadata: {list(uncovered)}")
