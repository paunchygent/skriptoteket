"""Expected replay build events for the two decided TASK-SKRIPT-39-04-17 exams.

Since TASK-SKRIPT-39-04-17, Fråga 1 of the two svenska_2 grammatik omprov exams
goes to review with a ``gap_count_mismatch`` admission event over anchors
``body:0008`` to ``body:0013``. Every other replay guard expectation stays as
strict as before: any event outside the formatting stage is unexpected, except
exactly that one decided admission event.
"""

from collections.abc import Iterable

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import DocxBuildEvent

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


def unexpected_build_events(exam: str, events: Iterable[DocxBuildEvent]) -> list[DocxBuildEvent]:
    """Events outside the formatting stage, except the one TASK-SKRIPT-39-04-17 admission.

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
        unexpected.append(event)
    return unexpected
