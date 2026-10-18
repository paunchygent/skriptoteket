"""Place a section's instructions: one native parent per run of questions, else a copy per item.

Exam.net carries only items, so an instruction that serves a run of questions becomes the
parent of that run, whatever kinds its questions have, review items included (D27). An
instruction the grouping marks as governing several questions serves exactly the items of
those questions, wherever the converter placed the chunks around it (step 3). An
instruction that reaches a single item, or a reach that skips an item between two reached
ones, is copied into exactly the items it reaches. An instruction printed inside an item's
own chunks keeps its source position there. Printed headings are runs of their own in the
same pass (``docx_instruction_runs``): over one question a heading opens its body, and
over two or more consecutive questions it opens their parent's instruction (T1, T2). A part
line that opens a parent (``PartLines.parents``) opens one over a single question too.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from types import MappingProxyType

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildEvent,
    ProducedMetadata,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_scoring import (
    InvalidTickValue,
    matching_score,
    point_shares,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_instruction_runs import (
    Joined,
    Placed,
    Run,
    instruction_runs,
    parent_groups,
    reaches,
    with_heading_runs,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_item_alignment import (
    AlignedItem,
    source_places,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    ExamManifest,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_lines import (
    NO_PART_LINES,
    PartLines,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_form import source_form
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_review import review_source_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    POINT_LABEL,
    QUESTION_HEADING_LABEL,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
    NativeItemReviewState,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import source_paragraphs

# A body paragraph and the anchor of the source chunk it shows.
_Shown = tuple[NativeParagraph, str]


def assign_question_headings(manifest: ExamManifest, chunks: tuple[DocxChunk, ...]) -> ExamManifest:
    """Move numbered/pointed single-question headings into that question before batching."""
    by_anchor = {chunk.anchor: chunk for chunk in chunks}
    moved: dict[str, str] = {}
    positions = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    for context in manifest.contexts:
        chunk = by_anchor[context.anchor]
        if (
            chunk.kind == "heading"
            and len(context.governs) == 1
            and (QUESTION_HEADING_LABEL.match(chunk.text) or POINT_LABEL.search(chunk.text))
        ):
            moved[context.anchor] = context.governs[0]
    if not moved:
        return manifest
    questions = tuple(
        replace(
            question,
            anchors=tuple(
                sorted(
                    (
                        *question.anchors,
                        *(a for a, owner in moved.items() if owner == question.question_id),
                    ),
                    key=positions.__getitem__,
                )
            ),
        )
        for question in manifest.questions
    )
    return replace(
        manifest,
        questions=questions,
        contexts=tuple(c for c in manifest.contexts if c.anchor not in moved),
        unplaced_anchors=tuple(a for a in manifest.unplaced_anchors if a not in moved),
    )


__all__ = [
    "Placed",
    "SectionInstructions",
    "place_section_instructions",
    "assign_question_headings",
]


@dataclass(frozen=True)
class SectionInstructions:
    """Items with ids and sequence, their parents, and where each instruction landed.

    ``landed`` maps the index of each instruction that reached an item to the anchors of the
    items it reached, in their bodies or under their parent.
    """

    items: tuple[NativeExamItem, ...]
    parents: tuple[NativeExamParent, ...]
    landed: Mapping[int, frozenset[str]]


@dataclass(frozen=True)
class QuestionPoints:
    item: NativeExamItem
    events: tuple[DocxBuildEvent, ...] = ()


def with_question_points(
    item: NativeExamItem,
    points: int | float,
    *,
    source_chunks: tuple[DocxChunk, ...],
    estimated: bool = False,
) -> QuestionPoints:
    """The question's one item owns its printed points, rubric and tick value included.

    ``points`` is what the question prints, or its share of a part's total, marked
    ``estimated`` (D6). The item's rubric is reshared in whole points and a matching item's
    tick value follows the total, so no total is changed alone. Points the rubric or ticks
    cannot carry send the item to teacher review.
    """
    updates: dict[str, object] = {"points": points, "points_estimated": estimated}
    try:
        if points <= 0:
            raise ValueError("the printed total gives the question no points")
        if item.kind is NativeExamItemKind.MATCHING:
            tick, total, rounded = matching_score(points, len(item.answer_key.match_pairs))
            updates.update(tick_points=tick, points=total, points_estimated=estimated or rounded)
        if item.criteria and sum(criterion.points for criterion in item.criteria) != points:
            shares = point_shares(points, len(item.criteria))
            if any(value < 1 or not float(value).is_integer() for value in shares):
                raise ValueError("the printed total cannot give each criterion whole points")
            updates["criteria"] = tuple(
                criterion.model_copy(update={"points": int(value)})
                for criterion, value in zip(item.criteria, shares, strict=True)
            )
    except InvalidTickValue:
        reason = (
            f"Tryckta {points:g} poäng ger mindre än 0,01 poäng per kryss. "
            "Kontrollera kategoriseringen."
        )
        source = review_source_item(source_chunks, reason)
        source = source.model_copy(
            update={
                "points": points,
                "points_estimated": estimated,
                "item_id": item.item_id,
                "sequence": item.sequence,
                "printed_label": item.printed_label,
                "source_anchor": item.source_anchor,
                "retry_source": item.retry_source,
                "review": source.review.model_copy(
                    update={
                        "confidence": item.review.confidence,
                        "reasons": tuple(
                            dict.fromkeys((*item.review.reasons, *source.review.reasons))
                        ),
                    }
                ),
            }
        )
        return QuestionPoints(
            source,
            (
                DocxBuildEvent(
                    stage="fallback",
                    code="invalid_tick_value",
                    anchors=tuple(chunk.anchor for chunk in source_chunks),
                ),
            ),
        )
    except ValueError:
        reason = (
            f"Tryckta {points:g} poäng kan inte fördelas på frågans bedömning. Kontrollera poängen."
        )
        review = item.review.model_copy(
            update={
                "state": NativeItemReviewState.REVIEW_REQUIRED,
                "reasons": tuple(dict.fromkeys((*item.review.reasons, reason))),
            }
        )
        return QuestionPoints(item.model_copy(update={"review": review}))
    return QuestionPoints(item.model_copy(update=updates))


def _unshown(aligned: AlignedItem, sources: Sequence[DocxChunk]) -> tuple[_Shown, ...]:
    """The source paragraphs of each chunk in ``sources`` the item does not show yet, each
    with its chunk.

    The item shows a chunk when one of its body paragraphs is aligned to it; its wording is
    never compared, so a reworded reply line aligned to the chunk counts as showing it and a
    line that only repeats its words does not (TASK-SKRIPT-39-04-13).
    """
    return tuple(
        (paragraph, chunk.anchor)
        for chunk in sources
        if not aligned.shows(chunk.anchor)
        for paragraph in source_paragraphs((chunk,))
    )


def _in_source_form(aligned: AlignedItem, sources: Sequence[DocxChunk]) -> AlignedItem:
    """The item with each instruction chunk in ``sources`` it shows in its source form.

    The body paragraphs aligned to such a chunk are that chunk: they give way, at the first
    one's place, to the chunk's source paragraphs with their marks and pictures, so a reply
    line that echoes an instruction without its picture never drops it. A response gap the
    item placed there stays, at its source location (``source_form``); when no unique source
    location exists, the item's paragraphs stay as they are, since the source form could not
    carry its response. A heading keeps the reply's line, which carries the printed label
    assembly reads.
    """
    answers = {gap.gap_id: gap.accepted_values for gap in aligned.item.gaps}
    for chunk in sources:
        if chunk.kind == "heading" or not aligned.shows(chunk.anchor):
            continue
        pairs = list(zip(aligned.item.body, aligned.chunks, strict=True))
        shown = [paragraph for paragraph, anchor in pairs if anchor == chunk.anchor]
        restored = source_form(chunk, shown, answers)
        if restored is None:
            continue
        at = aligned.chunks.index(chunk.anchor)
        kept = [(paragraph, anchor) for paragraph, anchor in pairs if anchor != chunk.anchor]
        aligned = _inserted(
            aligned.with_body(kept),
            at,
            tuple((paragraph, chunk.anchor) for paragraph in restored),
        )
    return aligned


def _inserted(aligned: AlignedItem, at: int, added: Sequence[_Shown]) -> AlignedItem:
    pairs = list(zip(aligned.item.body, aligned.chunks, strict=True))
    return aligned.with_body((*pairs[:at], *added, *pairs[at:]))


def _with_joined(
    aligned: AlignedItem, joined: Sequence[Joined], position: Mapping[str, int], first: int
) -> AlignedItem:
    """Place each joined instruction as one source-ordered unit among the body paragraphs.

    A chunk the item already shows keeps its place (``_in_source_form``); every other chunk
    of the instruction is placed in source order: right after the instruction's paragraphs
    that come before it in the source, or, with none, first when the instruction opens the
    item and otherwise before the first body paragraph whose source place comes after it. A
    paragraph's place is its aligned chunk's position, and an unaligned paragraph takes the
    place of the aligned paragraph before it (``source_places``). Every source chunk keeps
    its exact place, a shared picture included. An instruction no later paragraph follows
    ends the body.
    """
    for entry in joined:
        own = {chunk.anchor for chunk in entry.sources}
        for chunk in entry.sources:
            if aligned.shows(chunk.anchor):
                continue
            here = position[chunk.anchor]
            prior = [
                n
                for n, anchor in enumerate(aligned.chunks)
                if anchor in own and position[anchor] < here
            ]
            if prior:
                at = prior[-1] + 1
            elif entry.opens:
                at = 0
            else:
                places = source_places(aligned.chunks, position, first)
                at = next((n for n, place in enumerate(places) if place > here), len(places))
            aligned = _inserted(aligned, at, _unshown(aligned, (chunk,)))
    return aligned


def _item_id(index: int) -> str:
    return f"item_{index + 1:03d}"


def _parent_instruction(group: Sequence[Run]) -> tuple[NativeParagraph, ...]:
    """Every run's source chunks as positioned paragraphs, headings first, deduplicated.

    A shared picture stays at its exact place in the shared wording (F2); a picture the
    chunker could not show keeps its named placeholder there.
    """
    paragraphs: list[NativeParagraph] = []
    seen_anchors: set[str] = set()
    for run in sorted(group, key=lambda entry: (not entry.heading, entry.start)):
        for chunk in run.sources:
            if chunk.anchor not in seen_anchors:
                paragraphs.extend(source_paragraphs((chunk,)))
                seen_anchors.add(chunk.anchor)
    return tuple(paragraphs)


def place_section_instructions(
    chunks: tuple[DocxChunk, ...],
    ordered: list[Placed],
    instructions: tuple[ProducedMetadata, ...],
    governed: Mapping[str, frozenset[str]],
    title_anchors: frozenset[str] = frozenset(),
    own_anchors: frozenset[str] = frozenset(),
    part_lines: PartLines = NO_PART_LINES,
) -> SectionInstructions:
    """Build the parents and copy the instructions that stay with single items.

    ``governed`` maps each instruction anchor the grouping marks as governing two or more
    questions to every anchor those questions own. Such an instruction reaches exactly the
    items holding one of those anchors, whatever headings and instructions lie between them.

    An instruction printed inside an item's own chunks joins that item. Any other instruction
    opens the items of its run, which ends at the next section heading (a heading no item
    owns or one that opens a printed part, other than a lead-in label) or at the next
    instruction printed after one of the run's items. Points lines are structure and are
    never instruction text, except in a non-heading chunk the grouping marks as governing,
    which keeps its whole text (D40). A printed heading is a run starting at the heading
    under the same section rule: over one question it opens its body, unless it is a part
    line that opens a parent (``PartLines.parents``), which is the instruction of a parent
    with that one child; over two or more
    consecutive questions it is the first line of their parent's instruction, ahead of the
    run's other instruction lines in source order (T1, T2). Heading points become the
    parent's printed total, never instruction words. A heading whose run cannot form or
    join a parent opens the body of the run's first question, so its wording stays
    student-visible.
    The instructions that reach two or more consecutive items become the parent of
    exactly those items, whatever their kinds. An instruction that defines terms reaches only
    the run's items whose own chunks use one; a lead-in ending in a colon that introduces a
    question opening with quoted material reaches only the run's items that open with quotes.
    Every other instruction, and every instruction whose reach cannot be a parent, is copied
    into the items it reaches. An instruction an item prints inside its own chunks is placed
    at that position in the item's body, and a chunk the item already shows, by the source
    alignment of its body paragraphs, is never repeated.
    """
    positions = {c.anchor: i for i, c in enumerate(chunks)}
    item_sources = [
        [chunks[i] for i in sorted(positions[a] for a in anchors)] for _, anchors, _ in ordered
    ]
    runs, joined = instruction_runs(chunks, instructions, item_sources, positions, governed)
    runs, shape = with_heading_runs(
        chunks,
        ordered,
        runs,
        instructions,
        governed,
        positions,
        title_anchors,
        own_anchors,
        part_lines,
    )
    reached = reaches(chunks, ordered, runs, item_sources, positions, shape)
    groups = parent_groups(reached)
    parented: dict[tuple[int | None, int], set[int]] = {}
    for group in groups:
        for run in group:
            parented.setdefault((run.origin, run.start), set()).update(run.reach)
    carried: dict[int, list[DocxChunk]] = {}
    landed: dict[int, set[str]] = {}
    for k, entries in joined.items():
        for entry in entries:
            landed.setdefault(entry.origin, set()).update(ordered[k][1])
    for run in reached:
        if run.origin is not None and run.reach:
            for k in run.reach:
                landed.setdefault(run.origin, set()).update(ordered[k][1])
        covered = parented.get((run.origin, run.start), set())
        targets = [k for k in run.reach if k not in covered]
        if run.heading and not run.governs and len(run.reach) >= 2:
            # A section heading that forms no parent opens its first question only. A
            # governing heading reaches every question it governs (D40), like a governing
            # instruction that cannot be a parent.
            targets = targets[:1]
        for k in targets:
            carried.setdefault(k, []).extend(run.sources)
    items: list[NativeExamItem] = []
    for k, (first, _, aligned) in enumerate(ordered):
        item = aligned.item
        for run in reached:
            if run.heading and run.reach == (k,):
                label = run.question_label
                if label:
                    item = item.model_copy(
                        update={
                            "printed_label": run.raw[
                                label.start() : label.end(1 if label.group(1) else 2)
                            ].strip()
                        }
                    )
        aligned = _in_source_form(
            replace(aligned, item=item),
            [*(c for entry in joined.get(k, []) for c in entry.sources), *carried.get(k, [])],
        )
        aligned = _with_joined(aligned, joined.get(k, []), positions, first)
        aligned = _inserted(aligned, 0, _unshown(aligned, carried.get(k, [])))
        items.append(aligned.item.model_copy(update={"item_id": _item_id(k), "sequence": k + 1}))
    parents = tuple(
        NativeExamParent(
            parent_id=f"parent_{number:03d}",
            instruction=_parent_instruction(group),
            item_ids=tuple(_item_id(k) for k in group[0].reach),
        )
        for number, group in enumerate(groups, start=1)
    )
    return SectionInstructions(
        tuple(items),
        parents,
        MappingProxyType({o: frozenset(a) for o, a in landed.items()}),
    )
