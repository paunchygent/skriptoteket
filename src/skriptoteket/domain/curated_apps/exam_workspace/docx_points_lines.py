"""The one owner of every printed total, decided from document structure (TASK-SKRIPT-39-04-11).

A total line is a chunk that prints exactly one points label. Outside question spans it must
stand alone: a heading, or a points line (a label and at most two words); a prose sentence
that mentions a rate prints no total. Its label (``docx_points_labels``) and its place among
the questions give it exactly one owner, whatever the grouping tagged it as or where it
placed it:

- A part line opens a part: a standalone line with a part label, or a heading with no exam
  or question label. Parts nest: a part-labelled line opens an outer part that runs to the
  next part-labelled line; a part line with no part label (a numbered heading) opens an
  inner part that runs to the next part line of either kind. A part prints the total of the
  questions that start in it. A points line after the start of the part's last question,
  before the part's end, that prints that same total closes the part; it is the part's
  line too.
- A summary line, outside every question span, names two or more parts with a total each
  (``part_totals``). A part-labelled standalone line that prints no total of its own opens
  a part when a summary gives its part a total. A part's total is the one distinct value
  its own line and the summaries print for it; when they differ it opens no part (D3). A
  summary line is metadata: never an exam-total candidate, never a question line.
- A question line lies in a question's span, from the question's start to the next question
  start or part line of either kind: any total line there without an exam label. Outside
  every span, a question-labelled line ("Poäng: 2 poäng") heads the question right after
  it, or the last question when none follows. A question's lines print its own points:
  their one distinct value, or none when they differ.
- Outside every question span, any other standalone total line is an exam-total candidate.
  One distinct candidate value is the exam total; differing values give none (D3).

A question starts at its first own chunk that is no standalone total line and no part line,
so where the grouping places a points line or a part heading never moves a question's start.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import ExamManifest
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_labels import (
    part_identity,
    part_totals,
    points_label,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    points_line,
    printed_points,
)


@dataclass(frozen=True)
class PrintedQuestion:
    """A question's own anchors and what its question lines print.

    ``prints`` is true when its span prints points; ``points`` is their one distinct value,
    such as a heading's "(4 p)" with its "/4 p" line, and None when the lines differ.
    """

    anchors: tuple[str, ...]
    prints: bool
    points: int | float | None


@dataclass(frozen=True)
class PrintedPart:
    """A part's printed total, its part line's anchor and the questions that start in it.

    ``identity`` is the part its line names ("3" for "Del 3" and "Part 3, Question 1"), or
    None when the line names none, such as a numbered heading.
    """

    total: int | float
    questions: tuple[int, ...]
    opener: str
    identity: str | None = None


@dataclass(frozen=True)
class PrintedPoints:
    """Every printed total and its owner.

    ``owners`` maps each points line a question owns to that question's index. ``metadata``
    holds every other points line: part and exam lines, never exam text or review items.
    """

    questions: tuple[PrintedQuestion, ...] = ()
    parts: tuple[PrintedPart, ...] = ()
    exam_total: int | float | None = None
    owners: Mapping[str, int] = MappingProxyType({})
    metadata: frozenset[str] = frozenset()


NO_PRINTED_POINTS = PrintedPoints()


def line_points(chunk: DocxChunk) -> int | float | None:
    """The points a chunk prints when it is a points line and no heading, else None."""
    if chunk.kind == "heading" or not points_line(chunk.text):
        return None
    return printed_points((chunk,))


def _one_value(values: Iterable[int | float]) -> int | float | None:
    """The one distinct value the lines print, or None when they differ (D3)."""
    distinct = set(values)
    return distinct.pop() if len(distinct) == 1 else None


def _stands_alone(chunk: DocxChunk) -> bool:
    """A heading or a points line prints a total of its own; a prose sentence does not."""
    return chunk.kind == "heading" or points_line(chunk.text)


def _opens_part(chunk: DocxChunk) -> bool:
    label = points_label(chunk.text)
    return _stands_alone(chunk) and (label == "part" or (chunk.kind == "heading" and label is None))


def _summary_part(chunk: DocxChunk) -> bool:
    """A part-labelled standalone line printing no total, which a summary can give one."""
    return (
        _stands_alone(chunk)
        and points_label(chunk.text) == "part"
        and printed_points((chunk,)) is None
    )


def _starts(
    questions: tuple[tuple[str, ...], ...], positions: Mapping[str, int], lines: set[int]
) -> list[tuple[int, int]]:
    """Each question's start and number in source order: its first own chunk outside ``lines``."""
    starts: list[tuple[int, int]] = []
    for number, own in enumerate(questions):
        body = [positions[a] for a in own if a in positions and positions[a] not in lines]
        if body:
            starts.append((min(body), number))
    return sorted(starts)


def _spans(starts: list[tuple[int, int]], openers: Iterable[int], size: int) -> dict[int, int]:
    """Each chunk inside a question's span, from its start to the next start or part line."""
    bounds = sorted(openers)
    span_of: dict[int, int] = {}
    for rank, (start, number) in enumerate(starts):
        end = min([s for s, _ in starts[rank + 1 :]] + [o for o in bounds if o > start] + [size])
        for index in range(start, end):
            span_of[index] = number
    return span_of


def printed_points_plan(
    chunks: tuple[DocxChunk, ...], questions: tuple[tuple[str, ...], ...]
) -> PrintedPoints:
    """Classify every total line once; ``questions`` holds each question's own anchors."""
    positions = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    totals = {
        index: total
        for index, chunk in enumerate(chunks)
        if (total := printed_points((chunk,))) is not None
    }
    standalone = {index for index in totals if _stands_alone(chunks[index])}
    summary_named = {identity for chunk in chunks for identity, _ in part_totals(chunk.text)}
    # A part line a summary may total never starts a question, as a total line never does.
    unprinted = {
        index
        for index, chunk in enumerate(chunks)
        if _summary_part(chunk) and part_identity(chunk.text) in summary_named
    }
    own_openers = [index for index in totals if _opens_part(chunks[index])]
    starts = _starts(questions, positions, standalone | unprinted)
    if not starts:
        # Without questions nothing owns a total; every line stays source text.
        return NO_PRINTED_POINTS
    first_spans = _spans(starts, own_openers, len(chunks))
    summaries = [
        index
        for index, chunk in enumerate(chunks)
        if index not in first_spans and part_totals(chunk.text)
    ]
    summary_totals: dict[str, set[int | float]] = {}
    for index in summaries:
        for identity, total in part_totals(chunks[index].text):
            summary_totals.setdefault(identity, set()).add(total)
    openers = sorted(
        {
            *own_openers,
            *(index for index in unprinted if part_identity(chunks[index].text) in summary_totals),
        }
    )
    # A part line opens its part with the one distinct total it and the summaries print.
    part_total: dict[int, int | float | None] = {}
    for index in openers:
        named = part_identity(chunks[index].text)
        own_total = {totals[index]} if index in totals else set()
        summarised = summary_totals.get(named, set()) if named is not None else set()
        part_total[index] = _one_value({*own_total, *summarised})
    span_of = _spans(starts, openers, len(chunks))
    lines: dict[int, list[int]] = {number: [] for _, number in starts}
    candidates: set[int | float] = set()
    for index, total in totals.items():
        if index in openers:
            continue
        chunk = chunks[index]
        label = points_label(chunk.text)
        if index in span_of:
            if label != "exam":
                lines[span_of[index]].append(index)
        elif label == "question":
            # A question's points label outside its span heads the question right after it,
            # or the last question when none follows.
            following = next((n for s, n in starts if s > index), starts[-1][1])
            lines[following].append(index)
        elif _stands_alone(chunk):
            candidates.add(total)
    named_part = {index: part_identity(chunks[index].text) for index in openers}
    parts: list[PrintedPart] = []
    closers: set[int] = set()
    for opener in openers:
        # An outer part (one that names its part) runs to the next outer part line; an inner
        # part to the next part line of either kind.
        end = next(
            (
                index
                for index in openers
                if index > opener and (named_part[opener] is None or named_part[index] is not None)
            ),
            len(chunks),
        )
        members = tuple(number for start, number in starts if opener <= start < end)
        total = part_total[opener]
        if not members or total is None:
            continue
        last_start = max(start for start, number in starts if number == members[-1])
        closers.update(
            index
            for index in lines[members[-1]]
            if last_start < index < end and line_points(chunks[index]) == total
        )
        parts.append(PrintedPart(total, members, chunks[opener].anchor, named_part[opener]))
    printed = tuple(
        PrintedQuestion(
            anchors=own,
            prints=bool(own_lines := [i for i in lines.get(number, ()) if i not in closers]),
            points=_one_value(totals[i] for i in own_lines),
        )
        for number, own in enumerate(questions)
    )
    owners = {
        chunks[index].anchor: number
        for number, indices in lines.items()
        for index in indices
        if index not in closers and line_points(chunks[index]) is not None
    }
    metadata = frozenset(
        {
            *(
                chunks[index].anchor
                for index in totals
                if line_points(chunks[index]) is not None and chunks[index].anchor not in owners
            ),
            *(chunks[index].anchor for index in summaries),
        }
    )
    return PrintedPoints(
        questions=printed,
        parts=tuple(parts),
        exam_total=_one_value(candidates),
        owners=MappingProxyType(owners),
        metadata=metadata,
    )


def section_openers(parts: Iterable[PrintedPart]) -> frozenset[str]:
    """The part lines that open a section: each that changes the running part.

    A part line that repeats the identity of the part line before it, such as "Part 3,
    Question 2" after "Part 3, Question 1", continues that part. A line that names no part
    opens one, unless it lies inside a part that names its part ("Uppgift 1.1 (4 p)" under
    "DEL 1"): that outer part keeps running over all of its questions.
    """
    openers: list[str] = []
    running: str | None = None
    outer: frozenset[int] = frozenset()
    for part in parts:
        if part.identity is None and outer.issuperset(part.questions):
            continue
        if part.identity is None or part.identity != running:
            openers.append(part.opener)
        running = part.identity
        outer = frozenset(part.questions) if part.identity is not None else frozenset()
    return frozenset(openers)


def manifest_questions(manifest: ExamManifest) -> tuple[tuple[str, ...], ...]:
    """Each grouped question's own anchors, as its question family holds them."""
    return tuple(q.anchors for q in manifest.questions)


def assign_points_lines(manifest: ExamManifest, chunks: tuple[DocxChunk, ...]) -> ExamManifest:
    """Place every points line and part line by its owner alone, wherever the grouping put it.

    A question's own points line joins its anchors; every other points line is unplaced
    metadata. Each such line leaves every other placement: anchors, subparts, answer keys,
    contexts, title and header tags. A part-labelled line ("Del 2", "Part 2A: enrich (1
    point)") is never a question anchor, whatever number of questions its part holds: it is
    unplaced section structure in the same way, and so is a part heading with no part label
    over several questions. A part line with no part label over one question, such as
    "Uppgift 2: Verb (2 p)", joins that question's anchors as its own points line does and
    leaves every other placement, so the heading has one owner whatever the reply lists.
    Every part line scores its questions whatever its placement. Run after question headings
    join their questions.
    """
    plan = printed_points_plan(chunks, manifest_questions(manifest))
    by_anchor = {chunk.anchor: chunk for chunk in chunks}
    ids = [question.question_id for question in manifest.questions]
    sections = {
        part.opener
        for part in plan.parts
        if part.identity is not None
        or (len(part.questions) > 1 and by_anchor[part.opener].kind == "heading")
    }
    joins = {
        **{anchor: ids[number] for anchor, number in plan.owners.items()},
        **{
            part.opener: ids[part.questions[0]]
            for part in plan.parts
            if len(part.questions) == 1 and part.identity is None
        },
    }
    positions = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    placed = set(joins) | plan.metadata | sections
    questions = tuple(
        replace(
            question,
            anchors=tuple(
                sorted(
                    (
                        *(a for a in question.anchors if a not in placed),
                        *(a for a, owner in joins.items() if owner == question.question_id),
                    ),
                    key=positions.__getitem__,
                )
            ),
            subpart_anchors=tuple(a for a in question.subpart_anchors if a not in placed),
            key_anchors=tuple(a for a in question.key_anchors if a not in placed),
        )
        for question in manifest.questions
    )
    return replace(
        manifest,
        questions=questions,
        contexts=tuple(c for c in manifest.contexts if c.anchor not in placed),
        title_anchors=tuple(a for a in manifest.title_anchors if a not in placed),
        header=tuple(h for h in manifest.header if h.anchor not in placed),
        unplaced_anchors=tuple(
            sorted(
                {
                    *(a for a in manifest.unplaced_anchors if a not in placed),
                    *(a for a in plan.metadata if a not in joins),
                    *sections,
                },
                key=positions.__getitem__,
            )
        ),
    )
