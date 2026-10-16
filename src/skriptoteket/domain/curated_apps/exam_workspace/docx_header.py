"""Read source header metadata without admitting header lines as exam text."""

from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import question_families
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import ExamManifest
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import printed_points
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamHeader,
)


def _number(value: int | float) -> str:
    return f"{value:g}".replace(".", ",")


def apply_header(
    document: NativeExamDocument, manifest: ExamManifest, chunks: tuple[DocxChunk, ...]
) -> NativeExamDocument:
    """Attach source-ordered course and totals, mapping questions through source anchors.

    Item ids are allocated during assembly and do not identify grouped questions.
    Every split item keeps an anchor from its question's source instead.
    """
    by_anchor = {chunk.anchor: chunk for chunk in chunks}
    positions = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    headers = sorted(manifest.header, key=lambda entry: positions[entry.anchor])
    course = " ".join(
        text for h in headers if h.kind == "course" if (text := by_anchor[h.anchor].text.strip())
    )
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
        if any(h.kind == "part_total" for h in headers)
        else {}
    )
    parents = list(document.parents)
    items = list(document.items)
    for header in headers:
        if header.kind != "part_total":
            continue
        points = printed_points((by_anchor[header.anchor],))
        if points is None:
            continue
        anchors = frozenset().union(*(question_anchors[q] for q in header.governs))
        governed = {item.item_id for item in items if item.source_anchor in anchors}
        overlaps = [len(governed.intersection(parent.item_ids)) for parent in parents]
        if overlaps and max(overlaps) > 0:
            index = overlaps.index(max(overlaps))
            if parents[index].printed_total is None:
                parents[index] = parents[index].model_copy(update={"printed_total": points})
        elif len(header.governs) > 1:
            # User decision (2026-10-16): drop an unparented multi-question part total.
            # It has no part-level check; the exam total still checks all item points.
            continue
        elif len(header.governs) == 1 and len(governed) == 1:
            index = next(i for i, item in enumerate(items) if item.item_id in governed)
            item = items[index]
            if item.points is None:
                items[index] = item.model_copy(update={"points": points})
            elif item.points != points:
                reason = f"Tryckt delsumma {_number(points)} p, frågan har {_number(item.points)} p"
                review = item.review.model_copy(
                    update={"reasons": tuple(dict.fromkeys((*item.review.reasons, reason)))}
                )
                items[index] = item.model_copy(update={"review": review})
    return document.model_copy(
        update={
            "header": NativeExamHeader(course_hint=course or None, printed_total=total),
            "parents": tuple(parents),
            "items": tuple(items),
        }
    )
