"""Place a section's instructions: one native parent per run of questions, else a copy per item.

Exam.net carries only items, so an instruction that serves a run of questions becomes the
parent of that run, whatever kinds its questions have, review items included (D27). An
instruction the grouping marks as governing several questions serves exactly the items of
those questions, wherever the converter placed the chunks around it (step 3). An
instruction that reaches a single item, or a reach that skips an item between two reached
ones, is copied into exactly the items it reaches. An instruction printed inside an item's
own chunks keeps its source position there. Printed headings are runs of their own in the
same pass (``docx_instruction_runs``): over one question a heading opens its body, and
over two or more consecutive questions it opens their parent's instruction (T1, T2).
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
    folded,
    instruction_runs,
    parent_groups,
    reaches,
    with_heading_runs,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    ExamManifest,
)
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
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import (
    body_asset_ids,
    body_plain_text,
    body_text_lines,
    source_paragraphs,
)


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


def _lines(text: str) -> list[str]:
    return [line for raw in text.splitlines() if (line := " ".join(raw.split()))]


def _printed(item: NativeExamItem, text: str) -> bool:
    """Whether the item already prints the text as whole lines of its body."""
    wanted = _lines(text)
    shown = [
        *(part for line in item.plain_text_lines() for part in _lines(line)),
    ]
    return (
        not wanted
        or " ".join(wanted) in shown
        or any(shown[i : i + len(wanted)] == wanted for i in range(len(shown) - len(wanted) + 1))
    )


def _paragraph_content(paragraph: NativeParagraph) -> tuple[tuple[str, str], ...]:
    """Positioned content independent of how adjacent text runs were split."""
    parts: list[tuple[str, str]] = []
    for segment in paragraph.segments:
        if segment.kind == "text":
            if parts and parts[-1][0] == "text":
                parts[-1] = ("text", parts[-1][1] + segment.text)
            else:
                parts.append(("text", segment.text))
        elif segment.kind == "asset":
            parts.append(("asset", segment.asset_id))
        else:
            parts.append(("gap", segment.gap_id))
    return tuple(parts)


def _body_paragraphs(
    item: NativeExamItem,
    paragraphs: Sequence[NativeParagraph],
    delivered: list[NativeParagraph],
) -> tuple[NativeParagraph, ...]:
    """Omit only already-delivered content, accounting for each paragraph occurrence.

    A text echo is not a positioned picture paragraph, and an asset id identifies bytes,
    not a source occurrence. Each complete matching body paragraph consumes one source
    occurrence; repeated source paragraphs remain repeated. Text-only instructions keep
    the existing whole-line wording check.
    """
    kept: list[NativeParagraph] = []
    for paragraph in paragraphs:
        matching = next(
            (
                shown
                for shown in delivered
                if _paragraph_content(shown) == _paragraph_content(paragraph)
            ),
            None,
        )
        if matching is not None:
            delivered.remove(matching)
            continue
        text = body_plain_text((paragraph,))
        if not body_asset_ids((paragraph,)) and text and _printed(item, text):
            continue
        kept.append(paragraph)
    return tuple(kept)


def _with_paragraphs(
    item: NativeExamItem, paragraphs: Sequence[NativeParagraph], delivered: list[NativeParagraph]
) -> NativeExamItem:
    return item.model_copy(
        update={"body": (*_body_paragraphs(item, paragraphs, delivered), *item.body)}
    )


def _renders_one_of(paragraph: NativeParagraph, chunks: Sequence[str]) -> bool:
    text = folded(" ".join(body_text_lines((paragraph,))))
    return bool(text) and any(chunk.startswith(text) for chunk in chunks)


def _with_joined(
    item: NativeExamItem, joined: Sequence[Joined], delivered: list[NativeParagraph]
) -> NativeExamItem:
    """Place each joined instruction before the body paragraph that renders the next own chunk.

    Every source chunk keeps its exact place, a shared picture included; a paragraph the
    item's own body already holds is not placed again. The first body paragraph stands in
    when the item prints nothing of its own before the instruction. An instruction no
    paragraph can be located by ends the body.
    """
    for entry in joined:
        added = _body_paragraphs(item, source_paragraphs(entry.sources), delivered)
        at = (
            0
            if entry.opens
            else next(
                (k for k, p in enumerate(item.body) if _renders_one_of(p, entry.later)),
                len(item.body),
            )
        )
        item = item.model_copy(update={"body": (*item.body[:at], *added, *item.body[at:])})
    return item


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
    part_lines: frozenset[str] = frozenset(),
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
    under the same section rule: over one question it opens its body, and over two or more
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
    at that position in the item's body, and text the item already prints as whole lines is
    never repeated.
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
    carried: dict[int, list[NativeParagraph]] = {}
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
            if (
                run.heading
                and run.raw
                and not any(chunk.images or chunk.missing_images for chunk in run.sources)
                and _printed(ordered[k][2], run.raw)
            ):
                continue
            carried.setdefault(k, []).extend(source_paragraphs(run.sources))
    items: list[NativeExamItem] = []
    for k, (_, _, item) in enumerate(ordered):
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
        delivered = list(item.body)
        item = _with_joined(item, joined.get(k, []), delivered)
        item = _with_paragraphs(item, carried.get(k, []), delivered)
        items.append(item.model_copy(update={"item_id": _item_id(k), "sequence": k + 1}))
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
