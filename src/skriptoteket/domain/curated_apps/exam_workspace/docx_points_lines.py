"""The one owner of every printed total, decided from document structure (TASK-SKRIPT-39-04-11).

A total line is a chunk that prints exactly one points label. Outside question spans it must
stand alone: a heading, or a points line (a label and at most two words); a prose sentence
that mentions a rate prints no total. Its label (``docx_points_labels``) and its place among
the questions give it exactly one owner, whatever the grouping tagged it as or where it
placed it:

- A part line opens a part: a standalone line with a part label, or a heading with no exam
  or question label. The part runs to the next part line and prints the total of the
  questions that start in it. A points line after the start of the part's last question,
  before the next part line, that prints that same total closes the part; it is the part's
  line too.
- A question line lies in a question's span, from the question's start to the next question
  start or part line: any total line there without an exam label. Outside every span, a
  question-labelled line ("Poäng: 2 poäng") heads the question right after it, or the last
  question when none follows. A question's lines print its own points: their one distinct
  value, or none when they differ.
- Outside every question span, any other standalone total line is an exam-total candidate.
  One distinct candidate value is the exam total; differing values give none (D3).

A question starts at its first own chunk that is no standalone total line, so where the
grouping places a points line or a total heading never moves a question's start.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import ExamManifest
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_labels import points_label
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
    """A part's printed total, its part line's anchor and the questions that start in it."""

    total: int | float
    questions: tuple[int, ...]
    opener: str


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
    openers = sorted(index for index in totals if _opens_part(chunks[index]))
    standalone = {index for index in totals if _stands_alone(chunks[index])}
    starts: list[tuple[int, int]] = []
    for number, own in enumerate(questions):
        body = [positions[a] for a in own if a in positions and positions[a] not in standalone]
        if body:
            starts.append((min(body), number))
    if not starts:
        # Without questions nothing owns a total; every line stays source text.
        return NO_PRINTED_POINTS
    starts.sort()
    span_of: dict[int, int] = {}
    for rank, (start, number) in enumerate(starts):
        end = min(
            [s for s, _ in starts[rank + 1 :]] + [o for o in openers if o > start] + [len(chunks)]
        )
        for index in range(start, end):
            span_of[index] = number
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
    parts: list[PrintedPart] = []
    closers: set[int] = set()
    for rank, opener in enumerate(openers):
        end = openers[rank + 1] if rank + 1 < len(openers) else len(chunks)
        members = tuple(number for start, number in starts if opener <= start < end)
        if not members:
            continue
        total = totals[opener]
        last_start = max(start for start, number in starts if number == members[-1])
        closers.update(
            index
            for index in lines[members[-1]]
            if last_start < index < end and line_points(chunks[index]) == total
        )
        parts.append(PrintedPart(total, members, chunks[opener].anchor))
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
        chunks[index].anchor
        for index in totals
        if line_points(chunks[index]) is not None and chunks[index].anchor not in owners
    )
    return PrintedPoints(
        questions=printed,
        parts=tuple(parts),
        exam_total=_one_value(candidates),
        owners=MappingProxyType(owners),
        metadata=metadata,
    )


def manifest_questions(manifest: ExamManifest) -> tuple[tuple[str, ...], ...]:
    """Each grouped question's own anchors, as its question family holds them."""
    return tuple(q.anchors for q in manifest.questions)


def assign_points_lines(manifest: ExamManifest, chunks: tuple[DocxChunk, ...]) -> ExamManifest:
    """Place every points line and part heading by its owner alone, wherever the grouping put it.

    A question's own points line joins its anchors; every other points line is unplaced
    metadata. Each such line leaves every other placement: anchors, subparts, answer keys,
    contexts, title and header tags. A part heading over several questions is unplaced
    section structure in the same way, which placement opens the part's parent with. A part
    heading over one question scores that question whatever its placement, and only leaves
    the context, title and header tags: no tag drops it from the source. Run after question
    headings join their questions.
    """
    plan = printed_points_plan(chunks, manifest_questions(manifest))
    by_anchor = {chunk.anchor: chunk for chunk in chunks}
    headings = [part for part in plan.parts if by_anchor[part.opener].kind == "heading"]
    sections = {part.opener for part in headings if len(part.questions) > 1}
    untagged = {part.opener for part in headings} - sections
    positions = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    placed = set(plan.owners) | plan.metadata | sections
    owned = {a for question in manifest.questions for a in question.anchors}
    tagged = placed | untagged
    ids = [question.question_id for question in manifest.questions]
    questions = tuple(
        replace(
            question,
            anchors=tuple(
                sorted(
                    (
                        *(a for a in question.anchors if a not in placed),
                        *(
                            a
                            for a, owner in plan.owners.items()
                            if ids[owner] == question.question_id
                        ),
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
        contexts=tuple(c for c in manifest.contexts if c.anchor not in tagged),
        title_anchors=tuple(a for a in manifest.title_anchors if a not in tagged),
        header=tuple(h for h in manifest.header if h.anchor not in tagged),
        unplaced_anchors=tuple(
            sorted(
                {
                    *(a for a in manifest.unplaced_anchors if a not in placed),
                    *plan.metadata,
                    *sections,
                    *(untagged - owned),
                },
                key=positions.__getitem__,
            )
        ),
    )
