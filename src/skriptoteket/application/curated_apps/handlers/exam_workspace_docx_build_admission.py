"""Admit produced items through the native contract and chunk-role bookkeeping."""

import json

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


def _require_anchors(anchors: tuple[str, ...], state: DocxBuildState, seen: set[str]) -> None:
    unknown = [a for a in anchors if a not in state.known_anchors]
    if unknown:
        detail = f"unknown anchors {unknown}"
        raise _Rejected("anchor_unknown", detail, f"Okända källankare ({detail}).")
    taken = [a for a in anchors if a in state.claimed or a in state.key_anchors or a in seen] + [
        a for a in anchors if anchors.count(a) > 1
    ]
    if taken:
        detail = f"anchors already used {sorted(set(taken))}"
        raise _Rejected(
            "anchor_conflict", detail, f"Källstycket används redan av annat innehåll ({detail})."
        )


def _admit_keys(raw: JsonValue, state: DocxBuildState) -> None:
    anchors = raw if isinstance(raw, list) else []
    valid = [a for a in anchors if isinstance(a, str) and a in state.known_anchors]
    if len(valid) != len(anchors):
        state.record(
            "admission", "answer_key_anchor_unknown", detail=f"{len(anchors) - len(valid)} unknown"
        )
    for anchor in valid:
        if anchor not in state.claimed:
            state.key_anchors.add(anchor)
            state.claimed.add(anchor)


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
        produced = _parse(ProducedItem, raw)
        anchors = produced.source_anchors
        _require_anchors(anchors, state, seen)
        if produced.outcome == "review":
            cause = produced.review_reason or "ingen orsak angavs"
            reason = f"AI-tolkningen markerade frågan för granskning: {cause}"
            state.record("admission", "model_review", item=index, anchors=anchors)
            state.accepted.append((review_item(produced, reason), anchors))
            seen.update(anchors)
            return
        try:
            item = native_item(produced)
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
