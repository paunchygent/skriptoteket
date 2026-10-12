"""Place a section's instructions: one native parent per run of questions, else a copy per item.

Exam.net carries only items, so an instruction that serves a run of questions becomes the
parent of that run, whatever kinds its questions have, review items included (D27). An
instruction the grouping marks as governing several questions serves exactly the items of
those questions, wherever the converter placed the chunks around it (step 3). An
instruction that reaches a single item, or a reach that skips an item between two reached
ones, is copied into exactly the items it reaches. An instruction printed inside an item's
own chunks keeps its source position there.
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedMetadata
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
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)

Placed = tuple[int, tuple[str, ...], NativeExamItem]

# A question line that starts with its printed number.
_NUMBERED = re.compile(r"^\s*\d{1,3}[.)]\s")
# A question line that opens with quoted material, after any list label.
_OPENS_WITH_QUOTE = re.compile(r"^\s*(?:\w{1,3}[.)]\s*)?[\"“‘«„]")
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


@dataclass(frozen=True)
class _Run:
    """One instruction (or lines an item prints before its numbered line) and the items after it."""

    origin: int | None
    start: int
    sources: tuple[DocxChunk, ...]
    span: tuple[int, ...] = ()
    reach: tuple[int, ...] = ()
    governs: frozenset[str] = frozenset()


@dataclass(frozen=True)
class _Joined:
    """An instruction printed inside an item's own chunks, and where in the item it belongs."""

    origin: int
    texts: tuple[str, ...]
    later: tuple[str, ...]
    opens: bool


def _lines(text: str) -> list[str]:
    return [line for raw in text.splitlines() if (line := " ".join(raw.split()))]


def _printed(item: NativeExamItem, text: str) -> bool:
    """Whether the item already prints the text as whole lines of its title or body."""
    wanted = _lines(text)
    shown = [
        *_lines(item.title or ""),
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


def _folded(text: str) -> str:
    return " ".join(text.replace(_GAP_MARKER, " ").split()).casefold()


def _renders_one_of(paragraph: NativeParagraph, chunks: Sequence[str]) -> bool:
    text = _folded(
        "".join(
            segment.text if isinstance(segment, NativeTextSegment) else _GAP_MARKER
            for segment in paragraph.segments
            if isinstance(segment, (NativeTextSegment, NativeGapSegment))
        )
    )
    return bool(text) and any(chunk.startswith(text) for chunk in chunks)


def _with_joined(item: NativeExamItem, joined: Sequence[_Joined]) -> NativeExamItem:
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
    governed: Mapping[str, frozenset[str]],
) -> tuple[list[_Run], dict[int, list[_Joined]]]:
    """The instruction runs, the text joined into the item that prints it, and its instructions.

    An instruction the grouping marks as governing questions is never joined into an item.
    """
    spans = [(positions[s[0].anchor], positions[s[-1].anchor]) for s in item_sources]
    joined: dict[int, list[_Joined]] = {}
    runs: list[_Run] = []
    for origin, instruction in enumerate(instructions):
        at = sorted(positions[a] for a in instruction.source_anchors)
        sources = tuple(chunks[i] for i in at)
        governs = frozenset(
            anchor for a in instruction.source_anchors for anchor in governed.get(a, ())
        )
        owner = next((k for k, (lo, hi) in enumerate(spans) if lo < at[0] and at[-1] < hi), None)
        if governs:
            runs.append(_Run(origin, at[-1], sources, governs=governs))
        elif owner is not None:
            own = [c for c in item_sources[owner] if c.kind != "heading"]
            joined.setdefault(owner, []).append(
                _Joined(
                    origin=origin,
                    texts=tuple(chunk.text for chunk in sources),
                    later=tuple(_folded(c.text) for c in own if positions[c.anchor] > at[-1]),
                    opens=not any(positions[c.anchor] < at[0] for c in own),
                )
            )
        else:
            runs.append(_Run(origin, at[-1], sources))
    for item_chunks in item_sources:
        lines = [c for c in item_chunks if c.kind != "heading"]
        numbered = next((i for i, c in enumerate(lines) if _NUMBERED.match(c.text)), 0)
        if numbered:
            runs.append(_Run(None, positions[lines[numbered - 1].anchor], tuple(lines[:numbered])))
    return runs, joined


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
        sources = (
            tuple(c for c in run.sources if c.text.strip())
            if run.governs
            else tuple(
                c
                for c in run.sources
                if not points_line(c.text)
                and (c.kind != "heading" or positions[c.anchor] in labels)
            )
        )
        if not sources:
            reached.append(_Run(run.origin, run.start, ()))
            continue
        if run.governs:
            reach = tuple(
                k for k, (_, anchors, _) in enumerate(ordered) if run.governs.intersection(anchors)
            )
            reached.append(_Run(run.origin, run.start, sources, reach, reach, run.governs))
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


def _parent_groups(reached: list[_Run]) -> list[list[_Run]]:
    """Runs whose instruction reaches the same two or more consecutive items, of any kinds."""
    candidates: dict[tuple[int, ...], list[_Run]] = {}
    for run in reached:
        consecutive = all(b - a == 1 for a, b in zip(run.reach, run.reach[1:], strict=False))
        if run.origin is not None and len(run.reach) >= 2 and consecutive:
            candidates.setdefault(run.reach, []).append(run)
    groups: list[list[_Run]] = []
    taken: set[int] = set()
    for span, group in sorted(candidates.items()):
        if not taken.intersection(span):
            taken.update(span)
            groups.append(group)
    return groups


def place_section_instructions(
    chunks: tuple[DocxChunk, ...],
    ordered: list[Placed],
    instructions: tuple[ProducedMetadata, ...],
    governed: Mapping[str, frozenset[str]],
) -> SectionInstructions:
    """Build the parents and copy the instructions that stay with single items.

    ``governed`` maps each instruction anchor the grouping marks as governing two or more
    questions to every anchor those questions own. Such an instruction reaches exactly the
    items holding one of those anchors, whatever headings and instructions lie between them.

    An instruction printed inside an item's own chunks joins that item. Any other instruction
    opens the items of its run, which ends at the next section heading (a heading no item
    owns, other than a lead-in label) or at the next instruction printed after one of the
    run's items. Section headings and points lines are structure and are never instruction
    text, except in a chunk the grouping marks as governing, which keeps its whole text (D40).
    The instructions that reach two or more consecutive items become the parent of
    exactly those items, whatever their kinds. An instruction that defines terms reaches only
    the run's items whose own chunks use one; lines an item prints before its numbered
    question line are such an instruction too; a lead-in ending in a colon that introduces a
    question opening with quoted material reaches only the run's items that open with quotes.
    Every other
    instruction, and every instruction whose reach cannot be a parent, is copied into the items
    it reaches. An instruction an item prints inside its own chunks is placed at that position
    in the item's body, and text the item already prints as whole lines is never repeated.
    """
    positions = {c.anchor: i for i, c in enumerate(chunks)}
    item_sources = [
        [chunks[i] for i in sorted(positions[a] for a in anchors)] for _, anchors, _ in ordered
    ]
    runs, joined = _runs(chunks, instructions, item_sources, positions, governed)
    reached = _reaches(chunks, ordered, runs, item_sources, positions)
    groups = _parent_groups(reached)
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
        for k in run.reach:
            if k not in covered:
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
                    for run in sorted(group, key=lambda r: r.start)
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
