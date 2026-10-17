"""The one owner of a points line printed after a question (TASK-SKRIPT-39-04-11 D2).

A points line, such as "Poäng: 2 poäng", that follows a question is that question's own
chunk, whatever the grouping tagged it as: left unplaced, a shared context, a header line or
an answer key. Batching, AI-reply admission and the section split then all read it as the
question's own printed points; it never becomes a separate question or review item.

One line is no question's: a line after the last question of a section of two or more
questions that restates the total its section heading prints. It is the section's points
line, which the section split absorbs; a header tag on it is dropped.
"""

from dataclasses import replace

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import ExamManifest
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    POINT_LABEL,
    points_line,
    printed_points,
)


def line_points(chunk: DocxChunk) -> int | float | None:
    """The points a line prints when it is only a points line and no heading, else None."""
    if chunk.kind == "heading" or not points_line(chunk.text):
        return None
    return printed_points((chunk,))


def heading_total(chunk: DocxChunk) -> int | float | None:
    """The one total a heading prints, such as "Del 1: litteraturhistoria, 15 poäng"."""
    if chunk.kind != "heading" or len(POINT_LABEL.findall(chunk.text)) != 1:
        return None
    return printed_points((chunk,))


def assign_points_lines(manifest: ExamManifest, chunks: tuple[DocxChunk, ...]) -> ExamManifest:
    """Give each points line after a question to that question, except a section's line.

    A line belongs to the question that starts last before it when no heading outside a
    question lies between them. Run after question headings join their questions.
    """
    positions = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    own = {anchor for question in manifest.questions for anchor in question.anchors}
    starts = sorted((positions[q.anchors[0]], q.question_id) for q in manifest.questions)
    sections = [
        (index, total)
        for index, chunk in enumerate(chunks)
        if chunk.anchor not in own and (total := heading_total(chunk)) is not None
    ]
    owners: dict[str, str] = {}
    section_lines: set[str] = set()
    for index, chunk in enumerate(chunks):
        points = line_points(chunk)
        if chunk.anchor in own or points is None:
            continue
        preceding = [(start, qid) for start, qid in starts if start < index]
        if not preceding:
            continue
        start, question_id = preceding[-1]
        if any(
            chunks[between].kind == "heading" and chunks[between].anchor not in own
            for between in range(start + 1, index)
        ):
            continue
        heading = max((s for s in sections if s[0] < start), default=None)
        if heading is not None and heading[1] == points:
            section_end = min((s[0] for s in sections if s[0] > index), default=len(chunks))
            in_section = [s for s, _ in starts if heading[0] < s < section_end]
            if len(in_section) >= 2 and max(in_section) < index:
                section_lines.add(chunk.anchor)
                continue
        owners[chunk.anchor] = question_id
    untagged = {h.anchor for h in manifest.header} & section_lines
    if not owners and not untagged:
        return manifest
    questions = tuple(
        replace(
            question,
            anchors=tuple(
                sorted(
                    (
                        *question.anchors,
                        *(a for a, owner in owners.items() if owner == question.question_id),
                    ),
                    key=positions.__getitem__,
                )
            ),
            key_anchors=tuple(a for a in question.key_anchors if a not in owners),
        )
        for question in manifest.questions
    )
    return replace(
        manifest,
        questions=questions,
        contexts=tuple(c for c in manifest.contexts if c.anchor not in owners),
        title_anchors=tuple(a for a in manifest.title_anchors if a not in owners),
        header=tuple(
            h for h in manifest.header if h.anchor not in owners and h.anchor not in untagged
        ),
        unplaced_anchors=tuple(
            a for a in (*manifest.unplaced_anchors, *untagged) if a not in owners
        ),
    )
