"""The TASK-SKRIPT-39-04-17 guard helper admits exactly the one decided event."""

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildEvent,
    DocxBuildStage,
)
from tests.unit.domain.curated_apps.exam_workspace.recorded_build_events_support import (
    TASK_SKRIPT_39_04_17_ADMITTED_ANCHORS,
    TASK_SKRIPT_39_04_17_ADMITTED_CODE,
    TASK_SKRIPT_39_04_17_ADMITTED_EXAMS,
    unexpected_build_events,
)


def _event(
    stage: DocxBuildStage = "admission",
    code: str = TASK_SKRIPT_39_04_17_ADMITTED_CODE,
    anchors: tuple[str, ...] = TASK_SKRIPT_39_04_17_ADMITTED_ANCHORS,
) -> DocxBuildEvent:
    return DocxBuildEvent(stage=stage, code=code, anchors=anchors)


def test_decided_admission_on_either_omprov_exam_is_expected():
    for exam in TASK_SKRIPT_39_04_17_ADMITTED_EXAMS:
        assert unexpected_build_events(exam, [_event()]) == []


def test_formatting_events_are_never_reported():
    event = _event(stage="formatting", code="exact", anchors=("body:0008",))
    assert unexpected_build_events(TASK_SKRIPT_39_04_17_ADMITTED_EXAMS[0], [event]) == []


def test_same_code_with_other_anchors_is_still_unexpected():
    event = _event(anchors=("body:0008", "body:0009"))
    assert unexpected_build_events(TASK_SKRIPT_39_04_17_ADMITTED_EXAMS[0], [event]) == [event]


def test_other_admission_code_on_the_same_anchors_is_still_unexpected():
    event = _event(code="item_unbuildable")
    assert unexpected_build_events(TASK_SKRIPT_39_04_17_ADMITTED_EXAMS[1], [event]) == [event]


def test_decided_event_on_another_exam_is_still_unexpected():
    event = _event()
    assert unexpected_build_events("chapter_4_poetry_and_lyrics_quiz_med_facit", [event]) == [event]
