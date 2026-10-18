"""A question-owned context's place: never in another question's entry, joined at its source.

The grouping is the owner of every context it gives a question (``owned_contexts``, ruling
2026-10-18 c, review-3 N5). An entry of a reply that lists a context only another question
owns is not converted: it becomes its question's source-review item, and the context leaves
it for its owner (parent ruling 2026-10-18 a). A context an owner's item holds no entry for,
also one the reply lists as the title, an instruction or an answer key, joins that item. A
joined context shows its source paragraphs, marks and pictures at its source place in the
owner's item; the place is read from the source alignment of the item's body paragraphs
(``AlignedItem``), never from the wording of the reply.
"""

from dataclasses import dataclass

from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_one_item import (
    raw_anchors,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_heading_wording import shown_heading
from skriptoteket.domain.curated_apps.exam_workspace.docx_item_alignment import AlignedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    QUESTION_HEADING_LABEL,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import NativeParagraph
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import source_paragraphs

FOREIGN_CONTEXT_REASON = (
    "AI-tolkningen lade en annan frågas text i frågan. Kontrollera frågan och konvertera den igen."
)


@dataclass(frozen=True)
class ForeignContexts:
    """The reply's entries without other questions' owned contexts.

    ``refused`` are the questions whose entry listed such a context, in reply order;
    ``moved`` are those contexts, each once.
    """

    items: list[JsonValue]
    refused: tuple[tuple[str, ...], ...]
    moved: tuple[str, ...]


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


def _held_questions(raw: JsonValue, state: DocxBuildState) -> set[tuple[str, ...]]:
    return {state.question_by_anchor[a] for a in raw_anchors(raw) if a in state.question_by_anchor}


def without_foreign_contexts(items: list[JsonValue], state: DocxBuildState) -> ForeignContexts:
    """The one owner of which entries list another question's owned context.

    Such an entry leaves the reply; its questions become their source-review items. An
    entry that holds the context's owner keeps it.
    """
    owners = _context_owners(state)
    kept: list[JsonValue] = []
    refused: list[tuple[str, ...]] = []
    moved: list[str] = []
    for raw in items:
        held = _held_questions(raw, state)
        foreign = [a for a in raw_anchors(raw) if a in owners and not held & owners[a]]
        if foreign and held:
            moved.extend(foreign)
            refused.extend(sorted(held - set(refused), key=state.questions.index))
            continue
        kept.append(raw)
    return ForeignContexts(kept, tuple(refused), tuple(dict.fromkeys(moved)))


def _without_anchors(raw: JsonValue, dropped: set[str], state: DocxBuildState) -> JsonValue:
    """A title or instruction without ``dropped``, showing its remaining chunks' source text,
    or None when nothing remains."""
    listed = raw_anchors(raw)
    if not isinstance(raw, dict) or not dropped.intersection(listed):
        return raw
    remaining: list[JsonValue] = [a for a in listed if a not in dropped]
    if not remaining:
        return None
    text = "\n".join(state.chunk_by_anchor[a].text for a in listed if a not in dropped)
    return {**raw, "text": text, "source_anchors": remaining}


def without_held_owned_contexts(
    content: dict[str, JsonValue], items: list[JsonValue], state: DocxBuildState
) -> dict[str, JsonValue]:
    """``content`` whose title, instructions and answer keys no longer list a context an item
    entry's question owns: that item joins it (ruling 2026-10-18 c, review-3 N4)."""
    owners = _context_owners(state)
    held = set().union(*(_held_questions(raw, state) for raw in items))
    dropped = {context for context, questions in owners.items() if questions & held}
    if not dropped:
        return content
    keys = content.get("answer_key_anchors")
    raw_instructions = content.get("instructions")
    instructions: list[JsonValue] = [
        kept
        for raw in (raw_instructions if isinstance(raw_instructions, list) else ())
        if (kept := _without_anchors(raw, dropped, state)) is not None
    ]
    return {
        **content,
        "answer_key_anchors": [a for a in keys if a not in dropped]
        if isinstance(keys, list)
        else keys,
        "title": _without_anchors(content.get("title"), dropped, state),
        "instructions": instructions,
    }


def _places(aligned: AlignedItem, position: dict[str, int], first: int) -> list[int]:
    """Each body paragraph's source place: its aligned chunk's position.

    An unaligned paragraph takes the place of the aligned paragraph before it; with none
    before it, of the first aligned paragraph after it; with none at all, of the question's
    first own chunk.
    """
    known = [position[c] if c is not None and c in position else None for c in aligned.chunks]
    following = next((p for p in known if p is not None), first)
    places: list[int] = []
    for place in known:
        places.append(place if place is not None else places[-1] if places else following)
    return places


def joined_body(
    aligned: AlignedItem,
    passages: tuple[DocxChunk, ...],
    headings: tuple[DocxChunk, ...],
    own: tuple[DocxChunk, ...],
    state: DocxBuildState,
) -> tuple[NativeParagraph, ...]:
    """``aligned.item``'s body with the joined contexts and question headings at their source
    place.

    A reply paragraph aligned to a joined context or to one of the question's ``headings`` is
    that chunk: it leaves the body, and the chunk shows once, in its joined form. A context
    shows its source paragraphs, marks and pictures; a heading shows its wording without its
    points label and question number (``shown_heading``), the form its heading run in
    assembly gives it, so assembly finds it delivered. Each joined chunk stands after the body
    paragraphs whose place comes before it and before those whose place comes after it, in
    source order (``_places``).
    """
    position = {chunk.anchor: n for n, chunk in enumerate(state.chunks)}
    first = position[own[0].anchor] if own else len(position)
    shown = {
        c.anchor: source_paragraphs(
            (shown_heading(c, aligned.item, QUESTION_HEADING_LABEL.match(c.text)),)
        )
        for c in headings
    }
    shown |= {c.anchor: source_paragraphs((c,)) for c in passages}
    body: list[tuple[int, tuple[NativeParagraph, ...]]] = [
        (place, (paragraph,))
        for paragraph, chunk, place in zip(
            aligned.item.body,
            aligned.chunks,
            _places(aligned, position, first),
            strict=True,
        )
        if chunk not in shown
    ]
    for anchor in sorted(shown, key=position.__getitem__):
        place = position[anchor]
        at = next((n for n, (p, _) in enumerate(body) if p > place), len(body))
        body.insert(at, (place, shown[anchor]))
    return tuple(paragraph for _, paragraphs in body for paragraph in paragraphs)
