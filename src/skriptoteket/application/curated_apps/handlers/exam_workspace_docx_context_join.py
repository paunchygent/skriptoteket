"""A question-owned context's place: never in another question's entry, joined at its source.

The grouping is the owner of every context it gives a question (``owned_contexts``, ruling
2026-10-18 c, review-3 N5). An entry of a reply that lists a context only another question
owns loses it before any item is built, the way a part line leaves an entry it may not stay
in; the owner's item then joins it as a context no entry holds. A joined context shows its
source paragraphs, marks and pictures at its source place in the owner's item.
"""

from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_one_item import (
    raw_anchors,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_heading_wording import heading_wording
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import source_paragraphs


def _context_owners(state: DocxBuildState) -> dict[str, frozenset[tuple[str, ...]]]:
    """Each owned context's owning questions, read from the grouping's owner alone."""
    owners: dict[str, set[tuple[str, ...]]] = {}
    for anchor, contexts in state.owned_contexts.items():
        question = state.question_by_anchor.get(anchor)
        if question is None:
            continue
        for context in contexts:
            owners.setdefault(context, set()).add(question)
    return {context: frozenset(questions) for context, questions in owners.items()}


def without_foreign_contexts(
    items: list[JsonValue], state: DocxBuildState
) -> tuple[list[JsonValue], tuple[str, ...]]:
    """``items`` without the owned contexts an entry lists for a question that does not own
    them, and those contexts, each once.

    This is the one owner of which contexts leave an entry: a context the grouping gives
    a question as its own leaves every entry that holds none of its owner's anchors. An
    entry that holds the owner keeps it.
    """
    owners = _context_owners(state)
    kept: list[JsonValue] = []
    moved: list[str] = []
    for raw in items:
        listed = raw_anchors(raw)
        held = {state.question_by_anchor[a] for a in listed if a in state.question_by_anchor}
        foreign = [a for a in listed if a in owners and not held & owners[a]]
        moved.extend(foreign)
        kept.append(
            {**raw, "source_anchors": [a for a in listed if a not in foreign]}
            if foreign and isinstance(raw, dict)
            else raw
        )
    return kept, tuple(dict.fromkeys(moved))


def _text(paragraph: NativeParagraph) -> str:
    return "".join(s.text for s in paragraph.segments if isinstance(s, NativeTextSegment))


def joined_body(
    item: NativeExamItem,
    passages: tuple[DocxChunk, ...],
    own: tuple[DocxChunk, ...],
    state: DocxBuildState,
    headings: tuple[DocxChunk, ...],
) -> tuple[NativeParagraph, ...]:
    """``item``'s body with the joined contexts' source paragraphs, marks and pictures at
    their source place, both in source order: a context printed before the question's first
    own chunk opens the body; one printed after it follows the content of the question's
    leading heading, which is the body's first paragraph when it holds the heading's wording.
    """
    position = {chunk.anchor: n for n, chunk in enumerate(state.chunks)}
    first = position[own[0].anchor] if own else len(position)
    before = tuple(c for c in passages if position[c.anchor] < first)
    after = tuple(c for c in passages if position[c.anchor] > first)
    lead = 0
    if after and headings and own and headings[0].anchor == own[0].anchor and item.body:
        wording = heading_wording(headings[0], item).casefold()
        if wording and wording in _text(item.body[0]).casefold():
            lead = 1
    return (
        *source_paragraphs(before),
        *item.body[:lead],
        *source_paragraphs(after),
        *item.body[lead:],
    )
