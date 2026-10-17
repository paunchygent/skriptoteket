"""Read source header metadata without admitting header lines as exam text."""

from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import DocxBuildEvent
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import question_families
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import ExamManifest
from skriptoteket.domain.curated_apps.exam_workspace.docx_section_instructions import (
    replace_question_items,
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


@dataclass(frozen=True)
class HeaderApplication:
    document: NativeExamDocument
    events: tuple[DocxBuildEvent, ...]


def resolve_header_course(
    course_hint: str, course_key: str | None, courses: tuple[ExamCourse, ...]
) -> ExamCourseChoice | None:
    if course_key is not None:
        chosen = next((entry for entry in courses if entry.key == course_key), None)
        if chosen is None:
            raise ValueError(f"Unknown exam course key: {course_key}")
    else:
        match = match_course_hint(course_hint, courses)
        chosen = match.course if match.kind == "unique" else None
    return ExamCourseChoice(key=chosen.key, name=chosen.name) if chosen else None


def apply_header(
    document: NativeExamDocument,
    manifest: ExamManifest | None,
    chunks: tuple[DocxChunk, ...],
    *,
    course_key: str | None,
    courses: tuple[ExamCourse, ...],
) -> HeaderApplication:
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
    course = resolve_header_course(course_hint, course_key, courses)
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
    parents = document.parents
    items = list(document.items)
    events: list[DocxBuildEvent] = []
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
            own = (
                {
                    anchor
                    for question in manifest.questions
                    if question.question_id in header.governs
                    for anchor in question.anchors
                }
                if manifest is not None
                else set()
            )
            members = tuple(items[i] for i in indices)
            scored = with_question_points(
                members,
                points,
                source_chunks=tuple(chunk for chunk in chunks if chunk.anchor in own),
            )
            events.extend(scored.events)
            items, parents = replace_question_items(items, parents, members, scored)
            continue
        overlaps = [len(governed.intersection(parent.item_ids)) for parent in parents]
        if overlaps and max(overlaps) > 0:
            index = overlaps.index(max(overlaps))
            if parents[index].printed_total is None:
                parents = tuple(
                    parent.model_copy(update={"printed_total": points}) if i == index else parent
                    for i, parent in enumerate(parents)
                )
        elif len(header.governs) > 1:
            # User decision (2026-10-16): drop an unparented multi-question part total.
            # It has no part-level check; the exam total still checks all item points.
            continue
    return HeaderApplication(
        document.model_copy(
            update={
                "header": NativeExamHeader(
                    course=course, course_hint=course_hint or None, printed_total=total
                ),
                "parents": tuple(parents),
                "items": tuple(items),
            }
        ),
        tuple(events),
    )
