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
from dataclasses import dataclass
from types import MappingProxyType

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedMetadata
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_instruction_runs import (
    Joined,
    Placed,
    folded,
    instruction_runs,
    parent_groups,
    reaches,
    with_heading_runs,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItem,
    NativeExamParent,
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)

__all__ = ["Placed", "SectionInstructions", "place_section_instructions"]

_GAP_MARKER = "[___]"


@dataclass(frozen=True)
class SectionInstructions:
    """Items with ids and sequence, their parents, and where each instruction landed.

    ``landed`` maps the index of each instruction that reached an item to the anchors of the
    items it reached, in their bodies or under their parent.
    """

    items: tuple[NativeExamItem, ...]
    parents: tuple[NativeExamParent, ...]
    landed: Mapping[int, frozenset[str]]


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


def _paragraphs(item: NativeExamItem, texts: Sequence[str]) -> tuple[NativeParagraph, ...]:
    return tuple(
        NativeParagraph(segments=(NativeTextSegment(text=text),))
        for text in dict.fromkeys(texts)
        if not _printed(item, text)
    )


def _with_paragraphs(item: NativeExamItem, texts: list[str]) -> NativeExamItem:
    return item.model_copy(update={"body": (*_paragraphs(item, texts), *item.body)})


def _renders_one_of(paragraph: NativeParagraph, chunks: Sequence[str]) -> bool:
    text = folded(
        "".join(
            segment.text if isinstance(segment, NativeTextSegment) else _GAP_MARKER
            for segment in paragraph.segments
            if isinstance(segment, (NativeTextSegment, NativeGapSegment))
        )
    )
    return bool(text) and any(chunk.startswith(text) for chunk in chunks)


def _with_joined(item: NativeExamItem, joined: Sequence[Joined]) -> NativeExamItem:
    """Place each joined instruction before the body paragraph that renders the next own chunk.

    The first body paragraph stands in when the item prints nothing of its own before the
    instruction. An instruction no paragraph can be located by ends the body.
    """
    for entry in joined:
        added = _paragraphs(item, entry.texts)
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


def place_section_instructions(
    chunks: tuple[DocxChunk, ...],
    ordered: list[Placed],
    instructions: tuple[ProducedMetadata, ...],
    governed: Mapping[str, frozenset[str]],
    title_anchors: frozenset[str] = frozenset(),
    own_anchors: frozenset[str] = frozenset(),
) -> SectionInstructions:
    """Build the parents and copy the instructions that stay with single items.

    ``governed`` maps each instruction anchor the grouping marks as governing two or more
    questions to every anchor those questions own. Such an instruction reaches exactly the
    items holding one of those anchors, whatever headings and instructions lie between them.

    An instruction printed inside an item's own chunks joins that item. Any other instruction
    opens the items of its run, which ends at the next section heading (a heading no item
    owns, other than a lead-in label) or at the next instruction printed after one of the
    run's items. Points lines are structure and are never instruction text, except in a
    chunk the grouping marks as governing, which keeps its whole text (D40). A printed
    heading is a run starting at the heading under the same section rule: over one question
    it opens its body, and over two or more consecutive questions it is the first line of
    their parent's instruction, ahead of the run's other instruction lines in source order
    (T1, T2). A heading whose run cannot form or join a parent opens the body of the run's
    first question, so its wording stays student-visible.
    The instructions that reach two or more consecutive items become the parent of
    exactly those items, whatever their kinds. An instruction that defines terms reaches only
    the run's items whose own chunks use one; lines an item prints before its numbered
    question line are such an instruction too; a lead-in ending in a colon that introduces a
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
        chunks, ordered, runs, instructions, governed, positions, title_anchors, own_anchors
    )
    reached = reaches(chunks, ordered, runs, item_sources, positions, shape)
    groups = parent_groups(reached)
    parented: dict[tuple[int | None, int], set[int]] = {}
    for group in groups:
        for run in group:
            parented.setdefault((run.origin, run.start), set()).update(run.reach)
    carried: dict[int, list[str]] = {}
    landed: dict[int, set[str]] = {}
    for k, entries in joined.items():
        for entry in entries:
            landed.setdefault(entry.origin, set()).update(ordered[k][1])
    for run in reached:
        if run.origin is not None and run.reach:
            for k in run.reach:
                landed.setdefault(run.origin, set()).update(ordered[k][1])
        covered = parented.get((run.origin, run.start), set())
        wording = "\n".join(chunk.text for chunk in run.sources)
        targets = [k for k in run.reach if k not in covered]
        if run.heading and not run.governs and len(run.reach) >= 2:
            # A section heading that forms no parent opens its first question only. A
            # governing heading reaches every question it governs (D40), like a governing
            # instruction that cannot be a parent.
            targets = targets[:1]
        for k in targets:
            if run.heading and run.raw and _printed(ordered[k][2], run.raw):
                continue
            carried.setdefault(k, []).append(wording)
    items = tuple(
        _with_paragraphs(_with_joined(item, joined.get(k, [])), carried.get(k, [])).model_copy(
            update={"item_id": _item_id(k), "sequence": k + 1}
        )
        for k, (_, _, item) in enumerate(ordered)
    )
    parents = tuple(
        NativeExamParent(
            parent_id=f"parent_{number:03d}",
            instruction=tuple(
                dict.fromkeys(
                    chunk.text
                    for run in sorted(group, key=lambda r: (not r.heading, r.start))
                    for chunk in run.sources
                    if chunk.text.strip()
                )
            ),
            item_ids=tuple(_item_id(k) for k in group[0].reach),
        )
        for number, group in enumerate(groups, start=1)
    )
    return SectionInstructions(
        items, parents, MappingProxyType({o: frozenset(a) for o, a in landed.items()})
    )
