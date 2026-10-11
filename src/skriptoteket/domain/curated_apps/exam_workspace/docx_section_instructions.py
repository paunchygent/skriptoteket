"""Place a section's instructions: one native parent per run of questions, else a copy per item.

Exam.net carries only items, so an instruction that serves a run of questions becomes the
parent of that run. An instruction that reaches only some items of its run, or a run that
cannot be a parent, is copied into exactly the items it reaches.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildEvent,
    ProducedMetadata,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    POINT_LABEL,
    defined_terms,
    points_line,
    uses_term,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItem,
    NativeExamParent,
    NativeParagraph,
    NativeTextSegment,
)

Placed = tuple[int, tuple[str, ...], NativeExamItem]

# A question line that starts with its printed number.
_NUMBERED = re.compile(r"^\s*\d{1,3}[.)]\s")
# A question line that opens with quoted material, after any list label.
_OPENS_WITH_QUOTE = re.compile(r"^\s*(?:\w{1,3}[.)]\s*)?[\"“‘«„]")


@dataclass(frozen=True)
class SectionInstructions:
    """Items with ids and sequence, their parents, and the instructions that reached an item."""

    items: tuple[NativeExamItem, ...]
    parents: tuple[NativeExamParent, ...]
    reaching: frozenset[int]
    events: tuple[DocxBuildEvent, ...]


@dataclass(frozen=True)
class _Run:
    """One instruction (or lines an item prints before its numbered line) and the items after it."""

    origin: int | None
    start: int
    sources: tuple[DocxChunk, ...]
    span: tuple[int, ...] = ()
    reach: tuple[int, ...] = ()


def _item_text(item: NativeExamItem) -> str:
    return " ".join(" ".join((item.title or "", *item.plain_text_lines())).split())


def _with_paragraphs(item: NativeExamItem, texts: list[str], *, first: bool) -> NativeExamItem:
    shown = _item_text(item)
    added = tuple(
        NativeParagraph(segments=(NativeTextSegment(text=text),))
        for text in dict.fromkeys(texts)
        if " ".join(text.split()) not in shown
    )
    body = (*added, *item.body) if first else (*item.body, *added)
    return item.model_copy(update={"body": body})


def _lead_in_labels(chunks: tuple[DocxChunk, ...], lead_in: set[int], own: set[str]) -> set[int]:
    """Headings that label a stretch of an instruction lead-in, such as one passage of two.

    Such a heading prints no points and sits between instruction paragraphs that no item owns.
    """
    return {
        i
        for i in range(1, len(chunks) - 1)
        if chunks[i].kind == "heading"
        and chunks[i].anchor not in own
        and not POINT_LABEL.search(chunks[i].text)
        and {i - 1, i + 1} <= lead_in
        and chunks[i - 1].kind != "heading"
        and chunks[i + 1].kind != "heading"
    }


def _is_lead_in(chunk: DocxChunk) -> bool:
    return chunk.kind != "heading" and chunk.text.rstrip().endswith(":")


def _opens_with_quote(sources: Sequence[DocxChunk]) -> bool:
    """Whether the question's first own line after any heading and lead-in opens with a quote."""
    first = next((c for c in sources if c.kind != "heading" and not _is_lead_in(c)), None)
    return first is not None and bool(_OPENS_WITH_QUOTE.match(first.text))


def _item_id(index: int) -> str:
    return f"item_{index + 1:03d}"


def _runs(
    chunks: tuple[DocxChunk, ...],
    instructions: tuple[ProducedMetadata, ...],
    item_sources: list[list[DocxChunk]],
    positions: dict[str, int],
) -> tuple[list[_Run], dict[int, list[str]], set[int]]:
    """The instruction runs, the text joined into the item that prints it, and its instructions."""
    spans = [(positions[s[0].anchor], positions[s[-1].anchor]) for s in item_sources]
    joined: dict[int, list[str]] = {}
    joined_origins: set[int] = set()
    runs: list[_Run] = []
    for origin, instruction in enumerate(instructions):
        at = sorted(positions[a] for a in instruction.source_anchors)
        sources = tuple(chunks[i] for i in at)
        owner = next((k for k, (lo, hi) in enumerate(spans) if lo < at[0] and at[-1] < hi), None)
        if owner is not None:
            joined.setdefault(owner, []).extend(chunk.text for chunk in sources)
            joined_origins.add(origin)
        else:
            runs.append(_Run(origin, at[-1], sources))
    for item_chunks in item_sources:
        lines = [c for c in item_chunks if c.kind != "heading"]
        numbered = next((i for i, c in enumerate(lines) if _NUMBERED.match(c.text)), 0)
        if numbered:
            runs.append(_Run(None, positions[lines[numbered - 1].anchor], tuple(lines[:numbered])))
    return runs, joined, joined_origins


def _reaches(
    chunks: tuple[DocxChunk, ...],
    ordered: list[Placed],
    runs: list[_Run],
    item_sources: list[list[DocxChunk]],
    positions: dict[str, int],
) -> list[_Run]:
    """Each run with its span (the items up to its end) and the items its rule reaches."""
    own = {anchor for _, anchors, _ in ordered for anchor in anchors}
    lead_in = {positions[c.anchor] for run in runs for c in run.sources if not points_line(c.text)}
    labels = _lead_in_labels(chunks, lead_in, own)
    boundaries = [
        i
        for i, chunk in enumerate(chunks)
        if chunk.kind == "heading" and chunk.anchor not in own and i not in labels
    ]
    starts = sorted(run.start for run in runs)
    reached: list[_Run] = []
    for run in sorted(runs, key=lambda r: r.start):
        sources = tuple(
            c
            for c in run.sources
            if not points_line(c.text) and (c.kind != "heading" or positions[c.anchor] in labels)
        )
        if not sources:
            reached.append(_Run(run.origin, run.start, ()))
            continue
        following = [k for k, (position, _, _) in enumerate(ordered) if position >= run.start]
        first_item = next(
            (ordered[k][0] for k in following if ordered[k][0] > run.start), len(chunks)
        )
        end = min(
            next((i for i in boundaries if i > run.start), len(chunks)),
            next((s for s in starts if s > first_item), len(chunks)),
        )
        span = tuple(k for k in following if ordered[k][0] < end)
        terms = defined_terms("\n".join(chunk.text for chunk in sources))
        quoted = (
            bool(following)
            and _is_lead_in(sources[-1])
            and _opens_with_quote(item_sources[following[0]])
        )
        reach = tuple(
            k
            for k in span
            if (not terms or uses_term(terms, item_sources[k]))
            and (not quoted or _opens_with_quote(item_sources[k]))
        )
        reached.append(_Run(run.origin, run.start, sources, span, reach))
    return reached


def _parent_groups(
    reached: list[_Run], ordered: list[Placed]
) -> tuple[list[list[_Run]], list[DocxBuildEvent]]:
    """Runs whose instruction reaches every item of the same two or more items of one kind."""
    candidates: dict[tuple[int, ...], list[_Run]] = {}
    for run in reached:
        if run.origin is not None and len(run.span) >= 2 and run.reach == run.span:
            candidates.setdefault(run.span, []).append(run)
    groups: list[list[_Run]] = []
    events: list[DocxBuildEvent] = []
    taken: set[int] = set()
    for span, group in sorted(candidates.items()):
        if taken.intersection(span):
            continue
        if len({ordered[k][2].kind for k in span}) > 1:
            ids = ", ".join(_item_id(k) for k in span)
            events.append(
                DocxBuildEvent(
                    stage="admission",
                    code="parent_kinds_mixed",
                    anchors=tuple(c.anchor for run in group for c in run.sources),
                    detail=f"a section instruction serves items of different kinds ({ids}): "
                    "it is copied into each item",
                )
            )
            continue
        taken.update(span)
        groups.append(group)
    return groups, events


def place_section_instructions(
    chunks: tuple[DocxChunk, ...],
    ordered: list[Placed],
    instructions: tuple[ProducedMetadata, ...],
) -> SectionInstructions:
    """Build the parents and copy the instructions that stay with single items.

    An instruction printed inside an item's own chunks joins that item. Any other instruction
    opens the items of its run, which ends at the next section heading (a heading no item
    owns, other than a lead-in label) or at the next instruction printed after one of the
    run's items. Section headings and points lines are structure and are never instruction
    text. The instructions that reach every item of a run of two or more items of one kind
    become that run's parent. An instruction that defines terms reaches only the run's items
    whose own chunks use one; lines an item prints before its numbered question line are such
    an instruction too; a lead-in ending in a colon that introduces a question opening with
    quoted material reaches only the run's items that open with quotes. These instructions,
    and every instruction of a run that cannot be a parent, are copied into the items they
    reach.
    """
    positions = {c.anchor: i for i, c in enumerate(chunks)}
    item_sources = [
        [chunks[i] for i in sorted(positions[a] for a in anchors)] for _, anchors, _ in ordered
    ]
    runs, joined, joined_origins = _runs(chunks, instructions, item_sources, positions)
    reached = _reaches(chunks, ordered, runs, item_sources, positions)
    groups, events = _parent_groups(reached, ordered)
    parented = {id(run) for group in groups for run in group}
    carried: dict[int, list[str]] = {}
    reaching = set(joined_origins)
    for run in reached:
        if run.origin is not None and run.reach:
            reaching.add(run.origin)
        if id(run) in parented:
            continue
        wording = "\n".join(chunk.text for chunk in run.sources)
        for k in run.reach:
            carried.setdefault(k, []).append(wording)
    items = tuple(
        _with_paragraphs(
            _with_paragraphs(item, joined.get(k, []), first=False), carried.get(k, []), first=True
        ).model_copy(update={"item_id": _item_id(k), "sequence": k + 1})
        for k, (_, _, item) in enumerate(ordered)
    )
    parents = tuple(
        NativeExamParent(
            parent_id=f"parent_{number:03d}",
            instruction=tuple(
                dict.fromkeys(
                    chunk.text
                    for run in sorted(group, key=lambda r: r.start)
                    for chunk in run.sources
                    if chunk.text.strip()
                )
            ),
            item_ids=tuple(_item_id(k) for k in group[0].span),
        )
        for number, group in enumerate(groups, start=1)
    )
    return SectionInstructions(items, parents, frozenset(reaching), tuple(events))
