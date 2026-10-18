"""The runs a section placement is built from: instructions, headings, and their reach.

Every run is decided in one pass with one section rule: a section boundary is a heading
no item owns or a part line that changes the running part, other than a heading that labels
a stretch inside one instruction printed in several paragraphs. A part's opener in the points
plan is a heading here whatever its Word kind: the plan, not the Word style, decides that it
is section structure. A printed heading over
questions is a run of its own starting at the heading, reaching the questions up to the
next boundary, so a parent formed from same-reach runs opens with the heading by
construction (T1, T2). A heading a question owns reaches that question alone. A heading
the grouping marks as governing reaches exactly the governed questions (D40). Lines a
question prints before its own numbered lines belong to that question alone and form no run.
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedMetadata
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_heading_wording import shown_heading
from skriptoteket.domain.curated_apps.exam_workspace.docx_item_alignment import AlignedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_lines import PartLines
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    POINT_LABEL,
    QUESTION_HEADING_LABEL,
    defined_terms,
    points_line,
    uses_term,
)

Placed = tuple[int, tuple[str, ...], AlignedItem]

# A question line that opens with quoted material, after any list label.
_OPENS_WITH_QUOTE = re.compile(r"^\s*(?:\w{1,3}[.)]\s*)?[\"“‘«„]")


@dataclass(frozen=True)
class Run:
    """One instruction and the items after it.

    A heading run carries one printed heading: ``only`` is the item that owns the heading
    chunk, and ``raw`` is the heading as printed, before its wording loses the printed
    points label and question number. ``part`` marks a part line that opens a parent
    whatever its number of questions (``PartLines.parents``).
    """

    origin: int | None
    start: int
    sources: tuple[DocxChunk, ...]
    span: tuple[int, ...] = ()
    reach: tuple[int, ...] = ()
    governs: frozenset[str] = frozenset()
    heading: bool = False
    only: int | None = None
    raw: str = ""
    question_label: re.Match[str] | None = None
    part: bool = False


@dataclass(frozen=True)
class Joined:
    """An instruction printed inside an item's own chunks, and where in the item it belongs.

    ``sources`` are the instruction's exact source chunks in source order, pictures and
    offsets included, so the body it becomes keeps every chunk at its own place.
    """

    origin: int
    sources: tuple[DocxChunk, ...]
    opens: bool


def _is_lead_in(chunk: DocxChunk) -> bool:
    return chunk.kind != "heading" and chunk.text.rstrip().endswith(":")


def _opens_with_quote(sources: Sequence[DocxChunk]) -> bool:
    """Whether the question's first own line after any heading and lead-in opens with a quote."""
    first = next((c for c in sources if c.kind != "heading" and not _is_lead_in(c)), None)
    return first is not None and bool(_OPENS_WITH_QUOTE.match(first.text))


def _lead_in_labels(
    chunks: tuple[DocxChunk, ...],
    runs: list[Run],
    own: set[str],
    positions: dict[str, int],
    item_starts: list[int],
    openers: frozenset[str],
) -> set[int]:
    """Headings that label a stretch of an instruction lead-in, such as one passage of two.

    Such a heading prints no points and sits between instruction paragraphs that no item
    owns, and the lead-in it sits in serves the one question that follows it. A heading
    over a run of two or more questions is a section heading, never a label, even when
    instruction lines stand on both sides of it: the run before it ends there. A plan part
    opener (``openers``) is a heading here whatever its Word kind, as everywhere in the
    section rule.
    """

    def heading(index: int) -> bool:
        return chunks[index].kind == "heading" or chunks[index].anchor in openers

    lead_in = {positions[c.anchor] for run in runs for c in run.sources if not points_line(c.text)}
    provisional = {
        i
        for i in range(1, len(chunks) - 1)
        if heading(i)
        and chunks[i].anchor not in own
        and not POINT_LABEL.search(chunks[i].text)
        and {i - 1, i + 1} <= lead_in
        and not heading(i - 1)
        and not heading(i + 1)
    }
    labels = set()
    for i in provisional:
        end = next(
            (
                j
                for j in range(i + 1, len(chunks))
                if heading(j) and chunks[j].anchor not in own and j not in provisional
            ),
            len(chunks),
        )
        if sum(1 for start in item_starts if i < start < end) <= 1:
            labels.add(i)
    return labels


def instruction_runs(
    chunks: tuple[DocxChunk, ...],
    instructions: tuple[ProducedMetadata, ...],
    item_sources: list[list[DocxChunk]],
    positions: dict[str, int],
    governed: Mapping[str, frozenset[str]],
) -> tuple[list[Run], dict[int, list[Joined]]]:
    """The instruction runs, and the text joined into the item that prints it.

    An instruction the grouping marks as governing questions is never joined into an item.
    """
    spans = [(positions[s[0].anchor], positions[s[-1].anchor]) for s in item_sources]
    joined: dict[int, list[Joined]] = {}
    runs: list[Run] = []
    for origin, instruction in enumerate(instructions):
        at = sorted(positions[a] for a in instruction.source_anchors)
        sources = tuple(chunks[i] for i in at)
        governs = frozenset(
            anchor for a in instruction.source_anchors for anchor in governed.get(a, ())
        )
        owner = next((k for k, (lo, hi) in enumerate(spans) if lo < at[0] and at[-1] < hi), None)
        if governs:
            runs.append(Run(origin, at[-1], sources, governs=governs))
        elif owner is not None:
            joined.setdefault(owner, []).append(
                Joined(
                    origin=origin,
                    sources=sources,
                    # The item's own heading counts: an instruction printed after it
                    # never opens the body ahead of the heading's line.
                    opens=not any(positions[c.anchor] < at[0] for c in item_sources[owner]),
                )
            )
        else:
            runs.append(Run(origin, at[-1], sources))
    return runs, joined


@dataclass(frozen=True)
class SectionShape:
    """The one section rule for a document: its boundary headings and lead-in labels.

    ``parts`` are the boundaries that change the running part; ``nested`` the boundaries
    that open a part inside a part that names its part, which that part's run passes.
    """

    boundaries: list[int]
    labels: set[int]
    heading_anchors: frozenset[str]
    parts: frozenset[int] = frozenset()
    nested: frozenset[int] = frozenset()


def with_heading_runs(
    chunks: tuple[DocxChunk, ...],
    ordered: list[Placed],
    runs: list[Run],
    instructions: tuple[ProducedMetadata, ...],
    governed: Mapping[str, frozenset[str]],
    positions: dict[str, int],
    title_anchors: frozenset[str],
    own_anchors: frozenset[str],
    part_lines: PartLines,
) -> tuple[list[Run], SectionShape]:
    """Add one run per printed heading, under the same boundary rule as every other run.

    Every part's opener (``part_lines.openers``) is a printed heading whatever its Word kind.
    A part line that changes the running part (``part_lines.sections``) is a section boundary
    even when a question owns it, so the part before it never runs on into the part it opens.

    The document's opening heading is the exam title, never a question heading. A
    question's own heading chunk a reply lists as an instruction instead of in its item
    gets no heading run: it stays with the D42 return and check mark, because placement
    never silently repairs a misplaced own chunk.
    """
    own = {anchor for _, anchors, _ in ordered for anchor in anchors}
    owner = {a: k for k, (_, anchors, _) in enumerate(ordered) for a in anchors}
    labels = _lead_in_labels(
        chunks, runs, own, positions, [start for start, _, _ in ordered], part_lines.openers
    )
    boundaries = [
        i
        for i, chunk in enumerate(chunks)
        if (chunk.kind == "heading" or chunk.anchor in part_lines.openers)
        and (chunk.anchor not in own or chunk.anchor in part_lines.sections)
        and i not in labels
    ]
    boundary_anchors = {chunks[i].anchor for i in boundaries}
    held = {a for m in instructions for a in m.source_anchors}
    sole_origin = {
        m.source_anchors[0]: i for i, m in enumerate(instructions) if len(m.source_anchors) == 1
    }
    assigned = held | owner.keys() | governed.keys()
    headings: list[Run] = []
    for chunk in chunks:
        at = positions[chunk.anchor]
        if (
            (chunk.kind != "heading" and chunk.anchor not in part_lines.openers)
            or (not chunk.text.strip() and not chunk.images and not chunk.missing_images)
            or (at == 0 and chunk.anchor not in assigned)
            or chunk.anchor in title_anchors
        ):
            continue
        if chunk.anchor in owner:
            only: int | None = owner[chunk.anchor]
            governs: frozenset[str] = frozenset()
        elif chunk.anchor in boundary_anchors:
            if chunk.anchor in own_anchors and chunk.anchor in held:
                continue
            only = None
            governs = governed.get(chunk.anchor, frozenset())
        else:
            continue
        headings.append(
            Run(
                sole_origin.get(chunk.anchor),
                at,
                (chunk,),
                governs=governs,
                heading=True,
                only=only,
                raw=chunk.text,
                question_label=QUESTION_HEADING_LABEL.match(chunk.text),
                part=only is None and chunk.anchor in part_lines.parents,
            )
        )
    shape = SectionShape(
        boundaries,
        labels,
        frozenset(r.sources[0].anchor for r in headings),
        frozenset(i for i in boundaries if chunks[i].anchor in part_lines.sections),
        frozenset(i for i in boundaries if chunks[i].anchor in part_lines.nested),
    )
    return [*runs, *headings], shape


# Heading 4 and deeper, and a heading style without a level, rank below level 3.
_UNRANKED_LEVEL = 4


def _heading_rank(chunk: DocxChunk) -> int:
    level = chunk.paragraphs[0].heading_level if chunk.paragraphs else None
    return level if level is not None else _UNRANKED_LEVEL


def _span(
    run: Run,
    ordered: list[Placed],
    shape: SectionShape,
    starts: list[int],
    chunks: tuple[DocxChunk, ...],
) -> tuple[int, ...]:
    """The items after a run, up to the next section boundary or later instruction.

    A heading run passes its subsection headings: it ends at the next boundary heading of
    the same or a higher level, so a section title directly above a subsection heading
    still reaches its section's questions. A part line that changes the running part ends
    every run whatever its level, once the run has reached a question: a run directly above a
    part line serves that part. A run opening a part that names its part passes the part
    lines nested in it, so its line reaches every question of its part.
    """
    chunk_count = len(chunks)
    rank = _heading_rank(run.sources[0]) if run.heading else None
    following = [k for k, (position, _, _) in enumerate(ordered) if position >= run.start]
    first_item = next((ordered[k][0] for k in following if ordered[k][0] > run.start), chunk_count)
    end = min(
        next(
            (
                i
                for i in shape.boundaries
                if i > run.start
                and not (i in shape.parts and i <= first_item)
                and not (run.heading and run.start in shape.parts and i in shape.nested)
                and (rank is None or i in shape.parts or _heading_rank(chunks[i]) <= rank)
            ),
            chunk_count,
        ),
        next((s for s in starts if s > first_item), chunk_count),
    )
    return tuple(k for k in following if ordered[k][0] < end)


def _exact(run: Run, ordered: list[Placed]) -> tuple[int, ...]:
    return tuple(
        k for k, (_, anchors, _) in enumerate(ordered) if run.governs.intersection(anchors)
    )


def reaches(
    chunks: tuple[DocxChunk, ...],
    ordered: list[Placed],
    runs: list[Run],
    item_sources: list[list[DocxChunk]],
    positions: dict[str, int],
    shape: SectionShape,
) -> list[Run]:
    """Each run with its span (the items up to its end) and the items its rule reaches."""
    # A heading run never ends another run: a question's own heading starts its item,
    # and a section heading already ends a run as a boundary.
    starts = sorted(run.start for run in runs if not run.heading)
    reached: list[Run] = []
    for run in sorted(runs, key=lambda r: r.start):
        if run.heading:
            reach = (
                (run.only,)
                if run.only is not None
                else _exact(run, ordered)
                if run.governs
                else _span(run, ordered, shape, starts, chunks)
            )
            chunk = run.sources[0]
            # D2 splits every heading the same way, whether it opens one question
            # or governs a parent: only its wording is displayed.
            opens = len(reach) == 1 and not run.part
            shown = shown_heading(
                chunk, ordered[reach[0]][2].item if opens else None, run.question_label
            )
            if not reach:
                reached.append(Run(run.origin, run.start, (), heading=True, raw=run.raw))
                continue
            reached.append(
                Run(
                    run.origin,
                    run.start,
                    (shown,) if shown.text or shown.images or shown.missing_images else (),
                    reach,
                    reach,
                    run.governs,
                    heading=True,
                    only=run.only,
                    raw=run.raw,
                    question_label=run.question_label,
                    part=run.part,
                )
            )
            continue
        sources = (
            tuple(
                c
                for c in run.sources
                if (c.text.strip() or c.images or c.missing_images)
                and c.anchor not in shape.heading_anchors
            )
            if run.governs
            else tuple(
                c
                for c in run.sources
                if not points_line(c.text)
                and (c.kind != "heading" or positions[c.anchor] in shape.labels)
                and c.anchor not in shape.heading_anchors
            )
        )
        if not sources:
            reached.append(Run(run.origin, run.start, ()))
            continue
        if run.governs:
            reach = _exact(run, ordered)
            reached.append(Run(run.origin, run.start, sources, reach, reach, run.governs))
            continue
        span = _span(run, ordered, shape, starts, chunks)
        terms = defined_terms("\n".join(chunk.text for chunk in sources))
        following = [k for k, (position, _, _) in enumerate(ordered) if position >= run.start]
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
        reached.append(Run(run.origin, run.start, sources, span, reach))
    return reached


def parent_groups(reached: list[Run]) -> list[list[Run]]:
    """Runs whose instruction reaches the same two or more consecutive items, of any kinds,
    or the one item a part line that opens a parent reaches (``Run.part``): that line alone
    forms the one-child parent.

    A heading the grouping marks as governing joins a parent only when its scope equals
    that parent's items (D40 exact scope): it never lands on a wider parent, forms no
    parent here when no exact parent stands, and opens the body of its first question
    in placement instead. A section heading without a governing scope has only its
    heuristic reach, which an item inserted before its first question can narrow; such
    a heading still joins a wider parent that contains its reach. A section title over
    several subsection parents opens the first of them, ahead of its subsection heading.
    """
    candidates: dict[tuple[int, ...], list[Run]] = {}
    for run in reached:
        consecutive = all(b - a == 1 for a, b in zip(run.reach, run.reach[1:], strict=False))
        if (run.origin is not None or run.heading) and run.reach and consecutive:
            candidates.setdefault(run.reach, []).append(run)
    # Over one item only the part line itself forms the parent; an instruction reaching that
    # item alone stays the item's own text, as over any single item.
    candidates = {
        span: group if len(span) >= 2 else [run for run in group if run.part]
        for span, group in candidates.items()
    }
    candidates = {span: group for span, group in candidates.items() if group}
    groups: list[list[Run]] = []
    taken: set[int] = set()
    # An instruction-formed parent stands before a heading-only one: a heading over a
    # wider run never displaces the parent of exactly the items an instruction serves.
    ordered_candidates = sorted(
        candidates.items(), key=lambda entry: (all(run.heading for run in entry[1]), entry[0])
    )
    for span, group in ordered_candidates:
        if any(run.sources for run in group) and not taken.intersection(span):
            taken.update(span)
            groups.append(group)
    groups.sort(key=lambda group: group[0].reach)
    grouped = {id(run) for group in groups for run in group}
    for run in reached:
        if run.heading and run.only is None and len(run.reach) >= 2 and id(run) not in grouped:
            for group in groups:
                within = set(run.reach) <= set(group[0].reach)
                opens = not run.governs and run.reach[0] == group[0].reach[0]
                if (within or opens) and (not run.governs or set(run.reach) == set(group[0].reach)):
                    group.append(run)
                    break
    return groups
