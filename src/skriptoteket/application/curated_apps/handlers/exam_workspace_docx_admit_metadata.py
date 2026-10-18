"""Admit a batch reply's answer keys, title and instructions (TASK-SKRIPT-39-05-04).

The grouping decides ownership: a question's own chunk an item of the reply lists stays with
that item. A title or instruction holding an own chunk no item lists is an instruction that
stands only where assembly places it at its question (D42); the title keeps its other chunks.
A listed answer key that is an own chunk of a question an item holds is no answer key.
"""

from pydantic import JsonValue, ValidationError

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedMetadata
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_lines import line_points
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    POINT_LABEL,
    QUESTION_HEADING_LABEL,
    title_without_answer_key,
)
from skriptoteket.domain.errors import DomainError


def validation_detail(error: ValidationError) -> str:
    """Field locations, error types and the invariant a validator names; never the input."""
    return "; ".join(
        f"{'.'.join(str(part) for part in entry['loc'])}: "
        + (entry["msg"] if entry["type"] == "value_error" else entry["type"])
        for entry in error.errors()
    )


def free_anchors(
    anchors: tuple[str, ...], state: DocxBuildState, seen: set[str]
) -> tuple[str, ...]:
    """The anchors no earlier entry of this batch or an earlier batch already holds."""
    return tuple(
        dict.fromkeys(
            a for a in anchors if a not in seen and a not in state.claimed and a in state.owned
        )
    )


def admit_keys(
    raw: JsonValue, state: DocxBuildState, seen: set[str], item_held: frozenset[str]
) -> None:
    listed = tuple(a for a in raw if isinstance(a, str)) if isinstance(raw, list) else ()
    for anchor in free_anchors(listed, state, seen):
        if item_held.intersection(state.question_by_anchor.get(anchor, ())):
            continue
        state.key_anchors.add(anchor)
        seen.add(anchor)


def _source(
    metadata: ProducedMetadata, anchors: tuple[str, ...], state: DocxBuildState
) -> ProducedMetadata:
    """``metadata`` narrowed to ``anchors``, showing their source text: the reply's text may
    hold the wording of chunks it no longer holds."""
    text = "\n".join(state.chunk_by_anchor[a].text for a in anchors)
    return metadata.model_copy(update={"text": text, "source_anchors": anchors})


def admit_metadata(
    raw: JsonValue,
    field_name: str,
    state: DocxBuildState,
    seen: set[str],
    item_held: frozenset[str],
) -> None:
    try:
        metadata = ProducedMetadata.model_validate(raw)
    except ValidationError as error:
        state.record("admission", f"{field_name}_unparsed", detail=validation_detail(error))
        return
    listed = free_anchors(metadata.source_anchors, state, seen)
    listed = tuple(
        a
        for a in listed
        if not (
            a in state.question_by_anchor
            and (
                is_points_line(a, state)
                or state.chunk_by_anchor[a].kind == "heading"
                and (
                    QUESTION_HEADING_LABEL.match(state.chunk_by_anchor[a].text)
                    or POINT_LABEL.search(state.chunk_by_anchor[a].text)
                )
            )
        )
    )
    # The grouping decides ownership: a question's own chunk an item of the reply lists stays
    # with that item. A title or instruction holding another own chunk is an instruction that
    # stands only where assembly places it at its question (D42).
    own = frozenset(a for a in listed if a in state.question_by_anchor) - state.governing
    anchors = tuple(a for a in listed if a not in own.intersection(item_held))
    if not anchors:
        state.record("admission", "anchor_conflict", anchors=metadata.source_anchors)
        return
    if anchors != metadata.source_anchors:
        metadata = _source(metadata, anchors, state)
    else:
        metadata = metadata.model_copy(update={"source_anchors": anchors})
    if field_name == "title" and own.intersection(anchors):
        moved = tuple(a for a in anchors if a in own)
        state.instructions = (*state.instructions, _source(metadata, moved, state))
        seen.update(moved)
        anchors = tuple(a for a in anchors if a not in own)
        if not anchors:
            return
        metadata = _source(metadata, anchors, state)
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


def is_points_line(anchor: str, state: DocxBuildState) -> bool:
    """A question's own line that only prints its points (D2): its item reads the points."""
    return line_points(state.chunk_by_anchor[anchor]) is not None
