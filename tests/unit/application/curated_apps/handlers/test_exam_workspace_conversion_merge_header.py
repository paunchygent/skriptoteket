"""Progress deliveries keep metadata without replacing the teacher's saved header."""

from __future__ import annotations

from dataclasses import replace

from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_merge import (
    ConversionProgress,
    abandon_target,
    first_conversion,
    merge_conversion,
    target_from_update,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamHeader
from skriptoteket.protocols.docx_conversion_progress import ConversionUpdate
from tests.unit.application.curated_apps.handlers.exam_workspace_conversion_support import (
    choice,
    conversion_update,
    placeholder,
)


def _delivery(*, complete: bool, course: str, total: int, part_total: int) -> ConversionUpdate:
    update = conversion_update(
        [
            ("q1", [choice("p1", "Ett")]),
            ("q2", [choice("p2", "Två") if complete else placeholder("p2", "Källtext")]),
        ],
        pending=() if complete else ("q2",),
        parents=(("part", ("q1", "q2")),),
    )
    document = update.document.model_copy(
        update={
            "header": NativeExamHeader(course_hint=course, printed_total=total),
            "parents": (
                update.document.parents[0].model_copy(update={"printed_total": part_total}),
            ),
        }
    )
    return replace(update, document=document)


def test_second_and_third_delivery_replace_untouched_header_and_keep_parent_total() -> None:
    first = first_conversion(
        update=_delivery(complete=False, course="Svenska 2", total=36, part_total=15),
        progress=ConversionProgress.from_question_ids(["q1", "q2"]),
    )
    second = merge_conversion(
        head=first.document,
        progress=first.progress,
        target=target_from_update(
            _delivery(complete=True, course="Svenska 2 kursavslutande", total=38, part_total=17)
        ),
    )
    assert second.document.header == NativeExamHeader(
        course_hint="Svenska 2 kursavslutande", printed_total=38
    )
    assert second.document.parents[0].printed_total == 17
    assert second.document.parents[0].item_ids == tuple(i.item_id for i in second.document.items)

    third = merge_conversion(
        head=second.document,
        progress=second.progress,
        target=target_from_update(
            _delivery(complete=True, course="Svenska 3", total=40, part_total=19)
        ),
    )
    assert third.document.header == NativeExamHeader(course_hint="Svenska 3", printed_total=40)
    assert third.document.parents[0].printed_total == 19


def test_teacher_header_edit_wins_on_every_subsequent_delivery() -> None:
    first = first_conversion(
        update=_delivery(complete=False, course="Svenska 2", total=36, part_total=15),
        progress=ConversionProgress.from_question_ids(["q1", "q2"]),
    )
    teacher_header = NativeExamHeader(course_hint="Lärarens kurs", printed_total=42)
    saved = first.document.model_copy(update={"header": teacher_header, "revision": 2})
    second = merge_conversion(
        head=saved,
        progress=first.progress,
        target=target_from_update(
            _delivery(complete=True, course="Svenska 3", total=38, part_total=17)
        ),
    )
    third = merge_conversion(
        head=second.document,
        progress=second.progress,
        target=target_from_update(
            _delivery(complete=True, course="Svenska 4", total=40, part_total=19)
        ),
    )
    assert second.document.header == teacher_header
    assert third.document.header == teacher_header
    assert third.document.parents[0].printed_total == 19


def test_teacher_clearing_header_is_not_treated_as_missing_conversion_metadata() -> None:
    first = first_conversion(
        update=_delivery(complete=False, course="Svenska 2", total=36, part_total=15),
        progress=ConversionProgress.from_question_ids(["q1", "q2"]),
    )
    cleared = first.document.model_copy(update={"header": NativeExamHeader(), "revision": 2})
    merged = merge_conversion(
        head=cleared,
        progress=first.progress,
        target=target_from_update(
            _delivery(complete=True, course="Svenska 3", total=38, part_total=17)
        ),
    )
    assert merged.document.header == NativeExamHeader()


def test_abandoning_conversion_keeps_header_and_printed_parent_total() -> None:
    first = first_conversion(
        update=_delivery(complete=False, course="Svenska 2", total=36, part_total=15),
        progress=ConversionProgress.from_question_ids(["q1", "q2"]),
    )
    merged = merge_conversion(
        head=first.document,
        progress=first.progress,
        target=abandon_target(head=first.document, progress=first.progress, reason="Avbruten"),
    )
    assert merged.document.header == first.document.header
    assert merged.document.parents[0].printed_total == 15
    assert merged.document.items[1].review.reasons == ("Avbruten",)
