"""Batch admission against pending source and reusable facit evidence."""

import json

from pydantic import JsonValue, ValidationError

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import (
    SourceText,
    normalize_text,
    parse_build_entry,
    validate_build_entry,
    validate_source_text,
)


def _metadata_candidates(
    raw: JsonValue, pending_anchors: set[str], state: DocxBuildState
) -> list[SourceText]:
    candidates = raw if isinstance(raw, list) else [raw]
    valid: list[SourceText] = []
    for value in candidates:
        if value is None:
            continue
        try:
            if not isinstance(value, dict) or set(value) != {"text", "source_anchors"}:
                raise ValueError("Invalid metadata shape")
            metadata = SourceText.model_validate_json(json.dumps(value), strict=True)
            if not set(metadata.source_anchors) <= pending_anchors:
                raise ValueError("Metadata references frozen source")
            validate_source_text(metadata, state.chunks)
            valid.append(metadata)
        except (ValueError, ValidationError):
            continue
    return valid


def _admit_metadata(
    content: dict[str, JsonValue], pending_anchors: set[str], state: DocxBuildState
) -> None:
    titles = _metadata_candidates([content["title"]], pending_anchors, state)
    raw_instructions = content["instructions"]
    instructions = _metadata_candidates(
        raw_instructions if isinstance(raw_instructions, list) else [], pending_anchors, state
    )
    if titles and state.title is None:
        state.title = titles[0]
    state.instructions = tuple(dict.fromkeys((*state.instructions, *instructions)))
    metadata = (*state.instructions, *((state.title,) if state.title else ()))
    for chunk in state.pending:
        texts = [value.text for value in metadata if chunk.anchor in value.source_anchors]
        if (
            chunk.anchor not in state.key_anchors
            and texts
            and normalize_text(" ".join(texts)) == normalize_text(chunk.text)
        ):
            state.claimed.add(chunk.anchor)


def _admit_item(raw: JsonValue, pending_anchors: set[str], state: DocxBuildState) -> None:
    entry = parse_build_entry(raw)
    bindings = set(entry.source_anchors) | {e.anchor for e in entry.key_evidence}
    if entry.points_evidence is not None:
        bindings.add(entry.points_evidence.anchor)
    if not bindings <= pending_anchors or bindings & state.claimed:
        raise ValueError("Frågan hänvisar till redan behandlade eller okända källstycken.")
    item = validate_build_entry(entry, state.chunks)
    question_anchors = tuple(a for a in entry.source_anchors if a not in state.key_anchors)
    state.accepted.append((item, question_anchors))
    state.claimed.update(question_anchors)


def admit_batch(content: dict[str, JsonValue], state: DocxBuildState) -> None:
    """Admit independently valid entries without consuming shared answer keys."""
    entries = content.get("items")
    if set(content) != {"title", "instructions", "items"} or not isinstance(entries, list):
        state.failures = ("Svaret följer inte provets JSON-schema.",)
        return
    pending_anchors = {chunk.anchor for chunk in state.pending}
    _admit_metadata(content, pending_anchors, state)
    errors: list[str] = []
    for raw in entries:
        try:
            _admit_item(raw, pending_anchors, state)
        except (ValueError, ValidationError) as error:
            errors.append(
                "Frågan följer inte det inbyggda schemat."
                if isinstance(error, ValidationError)
                else str(error)
            )
    state.advance_pending(errors)
