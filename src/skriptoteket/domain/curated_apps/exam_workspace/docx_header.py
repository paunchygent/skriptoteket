"""Read source header metadata without admitting header lines as exam text."""

from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import question_families
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import ExamManifest
from skriptoteket.domain.curated_apps.exam_workspace.docx_section_instructions import (
    with_question_points,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import printed_points
from skriptoteket.domain.curated_apps.exam_workspace.exam_course_catalog import (
    ExamCourse,
    match_course_hint,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    ExamCourseChoice,
    NativeExamDocument,
    NativeExamHeader,
)


def apply_header(
    document: NativeExamDocument,
    manifest: ExamManifest | None,
    chunks: tuple[DocxChunk, ...],
    *,
    course_key: str | None,
    courses: tuple[ExamCourse, ...],
) -> NativeExamDocument:
    """Attach source-ordered course and totals, mapping questions through source anchors.

    Item ids are allocated during assembly and do not identify grouped questions.
    Every split item keeps an anchor from its question's source instead.
    """
    by_anchor = {chunk.anchor: chunk for chunk in chunks}
    positions = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    headers = sorted(manifest.header, key=lambda entry: positions[entry.anchor]) if manifest else []
    course_hint = " ".join(
        text for h in headers if h.kind == "course" if (text := by_anchor[h.anchor].text.strip())
    )
    if course_key is not None:
        chosen = next((entry for entry in courses if entry.key == course_key), None)
        if chosen is None:
            raise ValueError(f"Unknown exam course key: {course_key}")
    else:
        match = match_course_hint(course_hint, courses)
        chosen = match.course if match.kind == "unique" else None
    course = ExamCourseChoice(key=chosen.key, name=chosen.name) if chosen else None
    total = next(
        (
            value
            for h in headers
            if h.kind == "exam_total"
            if (value := printed_points((by_anchor[h.anchor],))) is not None
        ),
        None,
    )
    question_anchors = (
        {family.question_id: family.claims for family in question_families(manifest, chunks)}
        if manifest is not None and any(h.governs for h in headers)
        else {}
    )
    parents = list(document.parents)
    items = list(document.items)
    for header in headers:
        if header.kind not in {"part_total", "question_total"}:
            continue
        points = printed_points((by_anchor[header.anchor],))
        if points is None:
            continue
        anchors = frozenset().union(*(question_anchors[q] for q in header.governs))
        governed = {item.item_id for item in items if item.source_anchor in anchors}
        if len(header.governs) == 1:
            indices = [i for i, item in enumerate(items) if item.item_id in governed]
            scored = with_question_points(tuple(items[i] for i in indices), points)
            for i, item in zip(indices, scored, strict=True):
                items[i] = item
            continue
        overlaps = [len(governed.intersection(parent.item_ids)) for parent in parents]
        if overlaps and max(overlaps) > 0:
            index = overlaps.index(max(overlaps))
            if parents[index].printed_total is None:
                parents[index] = parents[index].model_copy(update={"printed_total": points})
        elif len(header.governs) > 1:
            # User decision (2026-10-16): drop an unparented multi-question part total.
            # It has no part-level check; the exam total still checks all item points.
            continue
    return document.model_copy(
        update={
            "header": NativeExamHeader(
                course=course, course_hint=course_hint or None, printed_total=total
            ),
            "parents": tuple(parents),
            "items": tuple(items),
        }
    )
