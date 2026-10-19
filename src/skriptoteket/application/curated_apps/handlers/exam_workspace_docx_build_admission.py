"""Admit one schema-valid batch response into the build state (TASK-SKRIPT-39-05-04).

The strict output schema limits every anchor to the batch's own chunks and every kind to the
batch's kinds. A grouped question is admitted as one item (TASK-SKRIPT-39-04-12 C3): a
question whose body the reply spreads over several entries, or merges into one entry with
another question's body, is refused and becomes its source review item, which the teacher
reconverts through the single-question retry. Admission otherwise never rejects or retries a
schema-valid response. A chunk two entries name stays with the first; the later entry
keeps its other chunks. A question the native contract cannot hold, a question the model
marks for review, and every chunk no entry names become review items that keep their
source text; a question's review item shows all its own chunks as printed. A chunk the
grouping gives a question as its own stays with the item that lists it, also when the reply
lists it as an answer key, the title or an instruction, and is no answer key when an item lists
another chunk of its question. A title or instruction holding an own chunk no item lists is an
instruction that stands only where assembly places it at its question (D42); the title keeps
its other chunks. A converted item that leaves out own chunks of its question holds them; those
whose wording it lacks show under a check mark as printed (D41, D4). A reply without points
takes the one points label its question's own chunks print (D3). A gap_fill item that makes a gap of
material its line talks about becomes a review item showing its question as printed (D43).
A part's line no question owns (``PrintedPart.opener``) leaves, before any item is built,
every entry when it opens a parent (``parent_openers``: DEL 4 over one question too, user
ruling 2026-10-18), and every entry for a question outside its part when it heads its one
question (review-2 F1, review-3 N1). An entry holding no question anchor is
no item (review-3 N2). Every moved line is recorded once; unless an item of its part lists it,
it stands as an instruction, which placement puts at its part's parent or question. Building
one question's item never fails the batch: an item that cannot be built becomes a review item
holding that question's own source text. A context the grouping gives a question as its owner
that no entry holds joins that question's item as its source paragraphs, and joins its review
item otherwise; it is never an item of its own (ruling 2026-10-18 c). An entry of another
question that lists such a context is not converted: its question becomes its source-review
item (``foreign_context_listed``), and the context, recorded once (``owned_context_moved``),
joins its owner (review-3 N5, parent ruling 2026-10-18 a). One the reply lists as the title,
an instruction or an answer key joins its owner's item too when an item entry holds the owner
(review-3 N4). Joined contexts and the question's printed headings stand at their source place,
read from the source alignment of the item's body paragraphs (review-3 N6). A question reported as
a type conflict leaves the batch for the pipeline to resend with the kind the source shows,
once: in the resend it is kept as converted.
"""

from collections import Counter
from collections.abc import Callable
from dataclasses import replace

from pydantic import JsonValue, ValidationError

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_admit_metadata import (
    admit_keys,
    admit_metadata,
    free_anchors,
    is_points_line,
    is_question_heading,
    validation_detail,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
    TypeConflict,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_context_join import (
    FOREIGN_CONTEXT_REASON,
    joined_body,
    without_foreign_contexts,
    without_held_owned_contexts,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_one_item import (
    raw_anchors,
    refuse_questions,
    refused_questions,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_produced_content import (
    normalized_content,
    with_heading_content,
    without_header_content,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedItem,
    ProducedMetadata,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_gap_material import (
    GAPPED_MATERIAL_REASON,
    gapped_material,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_item_alignment import (
    AcceptedEntry,
    AlignedItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_own_instructions import (
    left_out_chunks,
    with_left_out_mark,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_lines import (
    heading_openers,
    parent_openers,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    QUESTION_HEADING_LABEL,
    definition_context,
    with_accepted_forms,
    with_printed_points,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
    NativeParseOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import (
    FORMATTING_REASON,
    FormattingTransferError,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_gap_paragraphs import (
    GapCountMismatchError,
)

CONFLICT_WITHOUT_KIND_REASON = (
    "AI-tolkningen angav att frågan har en annan svarstyp men inte vilken. "
    "Kontrollera frågan manuellt."
)


Admitted = AcceptedEntry


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


class GaplessGapQuestionError(ValueError):
    """A converted gap_fill or inline_choice item that places no gap."""


def _built(
    index: int,
    anchors: tuple[str, ...],
    state: DocxBuildState,
    seen: set[str],
    build: Callable[[], AlignedItem],
) -> Admitted:
    """The item ``build`` makes, or its source review item when the item cannot be built."""
    try:
        return build(), anchors
    except FormattingTransferError as error:
        state.record(
            "admission",
            "formatting_transfer_failed",
            item=index,
            anchors=anchors,
            detail=str(error),
        )
        return state.printed(anchors, FORMATTING_REASON, seen)
    except ValidationError as error:
        return _source_review(
            index, anchors, state, seen, "native_contract_invalid", validation_detail(error)
        )
    except GaplessGapQuestionError as error:
        return _source_review(index, anchors, state, seen, "native_contract_invalid", str(error))
    except GapCountMismatchError as error:
        state.record(
            "admission", "gap_count_mismatch", item=index, anchors=anchors, detail=str(error)
        )
        return state.printed(anchors, error.reason, seen)
    except Exception as error:
        # Model output that breaks an assumption of the item builder affects only its question.
        return _source_review(index, anchors, state, seen, "item_unbuildable", type(error).__name__)


def _with_left_out(
    index: int,
    admitted: Admitted,
    state: DocxBuildState,
    seen: set[str],
    item_held: frozenset[str],
) -> Admitted:
    """A converted item holds the own chunks of its question it leaves out; those no body
    paragraph is aligned to show under a check mark as printed, a possible parsing issue (D41,
    D4).

    A left-out chunk is an own chunk of a question the item touches that no entry holds yet
    and no item of the reply lists, except as a points line alone (D2).
    """
    aligned, anchors = admitted
    item = aligned.item
    if item.review.parse_origin is not NativeParseOrigin.LLM_PARSED:
        return admitted
    own = set().union(*(state.question_by_anchor.get(a, ()) for a in anchors))
    left_out = tuple(
        c.anchor
        for c in state.pending
        if c.anchor in own
        and c.anchor not in seen
        # A points line another entry lists alone is no item; this one holds it (D2).
        and (c.anchor not in item_held or is_points_line(c.anchor, state))
    )
    # A left-out chunk the grouping lists as the question's facit is its answer key.
    keys = {a for a in left_out if a in state.grouped_keys}
    state.key_anchors.update(keys)
    seen.update(keys)
    # A left-out points line is held without a mark: the item already read its points (D2).
    held = {a for a in left_out if a not in keys and is_points_line(a, state)}
    seen.update(held)
    anchors = (*anchors, *(a for a in left_out if a in held))
    left_out = tuple(a for a in left_out if a not in keys and a not in held)
    if not left_out:
        return aligned, anchors
    seen.update(left_out)
    missing = left_out_chunks(aligned, [state.chunk_by_anchor[a] for a in left_out])
    if missing:
        moved = tuple(c.anchor for c in missing)
        state.record("admission", "own_chunks_left_out", item=index, anchors=moved)
        item = with_left_out_mark(item, missing)
    return replace(aligned, item=item), (*anchors, *left_out)


def _admit_item(
    index: int, raw: JsonValue, state: DocxBuildState, seen: set[str], item_held: frozenset[str]
) -> None:
    try:
        produced = ProducedItem.model_validate(raw)
    except ValidationError as error:
        # The question the entry names becomes one review item holding its source text.
        anchors = free_anchors(raw_anchors(raw), state, seen)
        detail = validation_detail(error)
        if not anchors:
            state.record("admission", "item_unparsed", item=index, detail=detail)
            return
        seen.update(anchors)
        state.accepted.append(_source_review(index, anchors, state, seen, "item_unparsed", detail))
        return
    anchors = free_anchors(produced.source_anchors, state, seen)
    if anchors != produced.source_anchors:
        state.record("admission", "anchor_conflict", item=index, anchors=produced.source_anchors)
    if not anchors:
        return
    produced = normalized_content(produced)
    # A header mixed into a reply may also have contaminated its rendered text.
    if state.header_anchors.intersection(produced.source_anchors):
        header_texts = tuple(
            state.chunk_by_anchor[a].text
            for a in state.header_anchors
            if a in state.chunk_by_anchor
        )
        try:
            produced = without_header_content(produced, header_texts)
        except ValidationError as error:
            seen.update(anchors)
            state.accepted.append(
                _source_review(
                    index, anchors, state, seen, "header_text_removed", validation_detail(error)
                )
            )
            return
    own = set().union(*(state.question_by_anchor.get(a, ()) for a in anchors))
    shown_lines = own | _part_lines_heading(anchors, state)
    headings = tuple(
        c
        for c in state.chunks
        if c.anchor in shown_lines
        and c.anchor not in state.header_anchors
        and is_question_heading(c)
    )
    if headings and set(anchors).issubset(c.anchor for c in headings):
        # A separately emitted heading is not a second question when the reply also
        # emits the question's body. Its leading anchor joins that body below.
        if (own - {c.anchor for c in headings}).intersection(item_held):
            return
    lines = {a for a in own if is_points_line(a, state)}
    if lines and set(anchors).issubset(lines) and (own - lines).intersection(item_held):
        # A separately emitted points line is no question: the item holding its question's
        # body holds it (D2).
        return
    leading = tuple(
        c.anchor
        for c in headings
        if c.anchor not in anchors and c.anchor not in seen | state.claimed
    )
    question = (*leading, *anchors)
    # A context the question owns that no entry holds joins its item (ruling 2026-10-18 c);
    # the question's first anchor stays the item's source anchor.
    joined = state.left_out_contexts(question, seen | item_held)
    anchors = (*question, *joined)
    produced = produced.model_copy(update={"source_anchors": anchors})
    produced = with_heading_content(produced, headings)
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
        try:
            # The kept reply is built like a converted one, so it meets the converted rules.
            produced = ProducedItem.model_validate(
                {**produced.model_dump(), "outcome": "converted", "kind": kind}
            )
        except ValidationError as error:
            detail = validation_detail(error)
            state.accepted.append(
                _source_review(index, anchors, state, seen, "item_unparsed", detail)
            )
            return
        state.kept_conflicts.update(anchors)
    if produced.outcome == "review":
        cause = produced.review_reason or "ingen orsak angavs"
        reason = f"AI-tolkningen markerade frågan för granskning: {cause}"
        state.record("admission", "model_review", item=index, anchors=anchors, detail=reason)
        state.accepted.append(state.printed(anchors, reason, seen))
        return
    if produced.kind is NativeExamItemKind.GAP_FILL:
        material = gapped_material(produced, (state.chunk_by_anchor[a] for a in anchors))
        if material:
            reason = f"{GAPPED_MATERIAL_REASON} {', '.join(f'”{m}”' for m in material)}"
            state.record("admission", "gapped_material", item=index, anchors=anchors, detail=reason)
            state.accepted.append(state.printed(anchors, reason, seen))
            return
    instructions = (
        *(a for m in state.instructions for a in m.source_anchors),
        *state.context_anchors,
    )

    def build() -> AlignedItem:
        context = definition_context(state.chunks, question, instructions)
        # The question's own paragraphs, also those the reply does not list (D3).
        shown = set(question).union(*(state.question_by_anchor.get(a, ()) for a in question))
        shown -= (state.key_anchors | state.grouped_keys) - set(question)
        shown -= state.header_anchors
        own = tuple(chunk for chunk in state.chunks if chunk.anchor in shown)
        scored = with_printed_points(
            with_accepted_forms(produced, context),
            (chunk for chunk in own if chunk.kind != "heading"),
        )
        aligned = aligned_native_item(
            scored,
            chunks=own,
            language=state.language,
            formatting_observer=lambda path: state.record_formatting(
                path, item=index, anchors=anchors
            ),
        )
        item = aligned.item
        if headings:
            printed_label = QUESTION_HEADING_LABEL.match(headings[0].text)
            if printed_label:
                item = item.model_copy(
                    update={
                        "printed_label": headings[0]
                        .text[
                            printed_label.start() : printed_label.end(
                                1 if printed_label.group(1) else 2
                            )
                        ]
                        .strip()
                    }
                )
        aligned = replace(aligned, item=item)
        passages = tuple(c for c in state.chunks if c.anchor in joined)
        if passages or headings:
            # The body's source alignment places each joined context and question heading
            # at its source place, in place of the reply's copy (review-3 N5/N6).
            aligned = joined_body(aligned, passages, headings, own, state)
            item = aligned.item
            own = (*passages, *own)
        if item.kind in (NativeExamItemKind.GAP_FILL, NativeExamItemKind.INLINE_CHOICE):
            if not item.gaps:
                # The model saves a teacher's zero-gap question, but a conversion that finds
                # no gap has misread the question: its source stays for review.
                raise GaplessGapQuestionError("gap_fill items need at least one gap")
        source_images = Counter(image.asset_id for chunk in own for image in chunk.images)
        emitted = Counter(item.body_asset_ids())
        if source_images != emitted:
            # A picture the reply did not place, or placed twice, would otherwise move,
            # vanish or double; the question's own source, pictures at their exact place,
            # is the honest result.
            missing = source_images - emitted
            extra = emitted - source_images
            raise ValueError(
                f"source pictures differ: missing {dict(missing)}, extra {dict(extra)}"
            )
        return aligned

    built = _built(index, anchors, state, seen, build)
    state.accepted.append(_with_left_out(index, built, state, seen, item_held))


def _part_lines_heading(anchors: tuple[str, ...], state: DocxBuildState) -> set[str]:
    """The part lines that head the one question these anchors hold.

    A part line no question owns that opens no parent (``heading_openers``) heads the one
    question of its part. Such a line is a heading of that question, which the join shows
    at its source place (CH4FRAG); the plan decides it, never the line's wording.
    """
    held = {state.question_by_anchor[a] for a in anchors if a in state.question_by_anchor}
    return {
        part.opener
        for part in heading_openers(state.plan.parts)
        if part.opener not in state.question_by_anchor
        and state.questions[part.questions[0]] in held
    }


def _without_part_lines(
    items: list[JsonValue], state: DocxBuildState
) -> tuple[list[JsonValue], tuple[str, ...]]:
    """``items`` without the part lines no entry may hold, and those lines, each once.

    This is the one owner of which part lines leave an entry. A part line no question owns
    (``PrintedPart.opener``) leaves every entry when it opens a parent (``parent_openers``),
    and every entry whose questions lie outside its part when it heads its one question
    (``heading_openers``). An entry that holds no question anchor is no item: it leaves the
    reply, its part lines among the moved ones, and its other chunks stay unlisted for the
    rules of chunks no entry holds.
    """
    parents = {a for a in parent_openers(state.plan.parts) if a not in state.question_by_anchor}
    headed = {
        part.opener: state.questions[part.questions[0]]
        for part in heading_openers(state.plan.parts)
        if part.opener not in state.question_by_anchor
    }
    kept: list[JsonValue] = []
    moved: list[str] = []
    for raw in items:
        listed = raw_anchors(raw)
        held = {state.question_by_anchor[a] for a in listed if a in state.question_by_anchor}
        lines = [a for a in listed if a in parents or (a in headed and headed[a] not in held)]
        moved.extend(lines)
        if not held:
            continue
        kept.append(
            {**raw, "source_anchors": [a for a in listed if a not in lines]}
            if lines and isinstance(raw, dict)
            else raw
        )
    return kept, tuple(dict.fromkeys(moved))


def admit_batch(content: dict[str, JsonValue], state: DocxBuildState) -> None:
    """Admit every entry once; chunks no entry names become review items."""
    seen: set[str] = set()
    raw_items = content.get("items")
    items = raw_items if isinstance(raw_items, list) else []
    refused = refused_questions(items, state)
    refuse_questions(refused, state, seen)
    items = [
        raw
        for raw in items
        if not any(state.question_by_anchor.get(a) in refused for a in raw_anchors(raw))
    ]
    items, moved = _without_part_lines(items, state)
    # An entry listing another question's owned context is its questions' source-review
    # item, and the context joins its owner's item (review-3 N5, parent ruling 2026-10-18 a).
    foreign = without_foreign_contexts(items, state)
    items = foreign.items
    for question in foreign.refused:
        own = tuple(
            c.anchor for c in state.pending if c.anchor in question and c.anchor not in seen
        )
        if own:
            state.record("admission", "foreign_context_listed", anchors=own)
            seen.update(own)
            state.accepted.append(state.printed(own, FOREIGN_CONTEXT_REASON, seen))
    if moved_contexts := free_anchors(foreign.moved, state, seen):
        state.record("admission", "owned_context_moved", anchors=moved_contexts)
    # A context an item entry's question owns joins that item, whatever other role the
    # reply gives it (ruling 2026-10-18 c, review-3 N4).
    content = without_held_owned_contexts(content, items, state)
    item_held = frozenset(a for raw in items for a in raw_anchors(raw))
    admit_keys(content.get("answer_key_anchors"), state, seen, item_held)
    if content.get("title"):
        admit_metadata(content["title"], "title", state, seen, item_held)
    raw_instructions = content.get("instructions")
    for raw in raw_instructions if isinstance(raw_instructions, list) else ():
        admit_metadata(raw, "instructions", state, seen, item_held)
    # Every moved part line is recorded; one no item of its part lists is an instruction,
    # which placement places.
    if moved := free_anchors(moved, state, seen):
        state.record("admission", "part_heading_moved", anchors=moved)
    if unheld := tuple(a for a in moved if a not in item_held):
        seen.update(unheld)
        by = state.chunk_by_anchor
        moved_lines = (ProducedMetadata(text=by[a].text, source_anchors=(a,)) for a in unheld)
        state.instructions = (*state.instructions, *moved_lines)
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
