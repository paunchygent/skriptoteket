"""Expected replay build events for the decided TASK-SKRIPT-39-04-17 and REP-0049 items.

Since TASK-SKRIPT-39-04-17, Fråga 1 of the two svenska_2 grammatik omprov exams
goes to review with a ``gap_count_mismatch`` admission event over anchors
``body:0008`` to ``body:0013``. Since TASK-SKRIPT-REP-0049 (rereview F4, decision A),
Fråga 5 of svenska_2 variant 2 goes to review with a ``formatting_transfer_failed``
admission event over anchors ``body:0045`` to ``body:0049``: its source repeats the
facit's analyses, which the reply did not emit. Every other replay guard expectation
stays as strict as before: any event outside the formatting stage is unexpected,
except exactly those decided admission events.
"""

from collections.abc import Iterable

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import DocxBuildEvent
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
    NativeParseOrigin,
)

TASK_SKRIPT_39_04_17_ADMITTED_EXAMS = (
    "svenska_2_grammatik_omprov_variant_1_med_facit",
    "svenska_2_grammatik_omprov_variant_2_med_facit",
)
TASK_SKRIPT_39_04_17_ADMITTED_CODE = "gap_count_mismatch"
TASK_SKRIPT_39_04_17_ADMITTED_ANCHORS = (
    "body:0008",
    "body:0009",
    "body:0010",
    "body:0011",
    "body:0012",
    "body:0013",
)

TASK_SKRIPT_REP_0049_ADMITTED_EXAM = "svenska_2_grammatik_omprov_variant_2_med_facit"
TASK_SKRIPT_REP_0049_ADMITTED_CODE = "formatting_transfer_failed"
TASK_SKRIPT_REP_0049_ADMITTED_ANCHORS = (
    "body:0045",
    "body:0046",
    "body:0047",
    "body:0048",
    "body:0049",
)


def is_pending_source_review(item: NativeExamItem) -> bool:
    """Whether the item keeps the D9 exemption: still pending source review."""
    return (
        item.review.state is NativeItemReviewState.REVIEW_REQUIRED
        and item.review.parse_origin is NativeParseOrigin.SOURCE_FALLBACK
    )


def unexpected_build_events(exam: str, events: Iterable[DocxBuildEvent]) -> list[DocxBuildEvent]:
    """Events outside the formatting stage, except the decided 39-04-17 and REP-0049 admissions.

    The decided event matches on stage, code, exam and anchors, never on detail text.
    """
    unexpected: list[DocxBuildEvent] = []
    for event in events:
        if event.stage == "formatting":
            continue
        if (
            event.stage == "admission"
            and event.code == TASK_SKRIPT_39_04_17_ADMITTED_CODE
            and exam in TASK_SKRIPT_39_04_17_ADMITTED_EXAMS
            and tuple(event.anchors) == TASK_SKRIPT_39_04_17_ADMITTED_ANCHORS
        ):
            continue
        if (
            event.stage == "admission"
            and event.code == TASK_SKRIPT_REP_0049_ADMITTED_CODE
            and exam == TASK_SKRIPT_REP_0049_ADMITTED_EXAM
            and tuple(event.anchors) == TASK_SKRIPT_REP_0049_ADMITTED_ANCHORS
        ):
            continue
        unexpected.append(event)
    return unexpected
