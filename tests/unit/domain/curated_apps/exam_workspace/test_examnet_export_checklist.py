"""Unit tests for the Exam.net import loss checklist (Q15-Q17).

Each listed loss and each unlisted neighbour, plus the writer-mechanics edge where
the rounded gap share floors to zero and the package carries no gap mapping.
"""

from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiInteractionType,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_xml import (
    QTI_NAMESPACE,
    gap_point_values,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_export_checklist import (
    ExamNetExportChecklistAllOrNothing,
    ExamNetExportChecklistCriterion,
    ExamNetExportChecklistFreeTextCriteria,
    ExamNetExportChecklistRoundedGaps,
    native_exam_export_checklist,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_criteria import (
    NativeExamCriterion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
    NativeGap,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from tests.unit.domain.curated_apps.exam_workspace.examnet_qti_export_test_support import (
    document_of,
    review_complete,
    text_body,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import plain_body


def _free_text_item(
    *,
    sequence: int = 1,
    item_id: str = "item_001",
    points: int = 3,
    criteria: tuple[NativeExamCriterion, ...] = (),
    text: str = "Resonera om satsdelar.",
    printed_label: str | None = None,
) -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.FREE_TEXT,
        writing_lines=8,
        printed_label=printed_label,
        body=text_body(text),
        points=points,
        criteria=criteria,
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=review_complete(),
    )


def _multiple_response_item(
    *,
    sequence: int = 1,
    item_id: str = "item_001",
    points: int = 5,
    correct: int = 3,
) -> NativeExamItem:
    choices = tuple(
        NativeChoice(choice_id=f"choice_{index:03d}", body=plain_body(f"Alternativ {index}"))
        for index in range(1, 5)
    )
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.MULTIPLE_RESPONSE,
        body=text_body("Välj alla korrekta alternativ."),
        points=points,
        choices=choices,
        answer_key=NativeAnswerKey(
            origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
            correct_choice_ids=tuple(choice.choice_id for choice in choices[:correct]),
        ),
        review=review_complete(),
    )


def _gap_fill_item(
    *,
    sequence: int = 1,
    item_id: str = "item_001",
    points: int | float = 5,
    gaps: int = 3,
) -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.GAP_FILL,
        body=tuple(
            NativeParagraph(
                heading_level=None,
                segments=(
                    NativeTextSegment(text=f"Lucka {index}: ", marks=()),
                    NativeGapSegment(gap_id=f"gap_{index:03d}"),
                ),
            )
            for index in range(1, gaps + 1)
        ),
        points=points,
        gaps=tuple(
            NativeGap(gap_id=f"gap_{index:03d}", accepted_values=(f"svar {index}",))
            for index in range(1, gaps + 1)
        ),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED),
        review=review_complete(),
    )


def _with_parent(document: NativeExamDocument, item_ids: tuple[str, ...]) -> NativeExamDocument:
    item_by_id = {item.item_id: item for item in document.items}
    return document.model_copy(
        update={
            "parents": (
                NativeExamParent(
                    parent_id="parent_001",
                    place=item_by_id[item_ids[0]].sequence - 1,
                    instruction=text_body("Gemensam instruktion."),
                    item_ids=item_ids,
                ),
            )
        }
    )


def test_free_text_with_criteria_lists_each_criterion_text_and_points() -> None:
    item = _free_text_item(
        points=3,
        criteria=(
            NativeExamCriterion(text="Ett korrekt exempel.", points=2),
            NativeExamCriterion(text="En korrekt förklaring.", points=1),
        ),
    )

    entries = native_exam_export_checklist(document_of((item,)))

    assert entries == (
        ExamNetExportChecklistFreeTextCriteria(
            item_id="item_001",
            question_text="Resonera om satsdelar.",
            points=3,
            criteria=(
                ExamNetExportChecklistCriterion(text="Ett korrekt exempel.", points=2),
                ExamNetExportChecklistCriterion(text="En korrekt förklaring.", points=1),
            ),
        ),
    )


def test_free_text_without_criteria_lists_nothing() -> None:
    item = _free_text_item()

    assert native_exam_export_checklist(document_of((item,))) == ()


def test_shared_subquestion_all_or_nothing_at_two_points_or_more_is_listed() -> None:
    uneven = _multiple_response_item(item_id="item_001", sequence=1, points=5, correct=3)
    even = _multiple_response_item(item_id="item_002", sequence=2, points=4, correct=2)
    one_point = _multiple_response_item(item_id="item_003", sequence=3, points=1, correct=3)
    document = _with_parent(
        document_of((uneven, even, one_point)),
        (uneven.item_id, even.item_id, one_point.item_id),
    )

    entries = native_exam_export_checklist(document)

    assert entries == (
        ExamNetExportChecklistAllOrNothing(
            item_id="item_001",
            question_text="Välj alla korrekta alternativ.",
            points=5,
        ),
    )


def test_standalone_all_or_nothing_item_lists_nothing() -> None:
    item = _multiple_response_item(points=5, correct=3)

    assert native_exam_export_checklist(document_of((item,))) == ()


def test_folded_single_child_parent_lists_no_all_or_nothing_loss() -> None:
    item = _multiple_response_item(points=5, correct=3)
    document = _with_parent(document_of((item,)), (item.item_id,))

    assert native_exam_export_checklist(document) == ()


def test_folded_single_child_parent_keeps_the_childs_own_loss() -> None:
    item = _free_text_item(
        sequence=1,
        item_id="item_001",
        printed_label="c",
        points=2,
        criteria=(NativeExamCriterion(text="Rätt begrepp.", points=2),),
    )
    document = _with_parent(document_of((item,)), (item.item_id,))

    entries = native_exam_export_checklist(document)

    assert entries == (
        ExamNetExportChecklistFreeTextCriteria(
            item_id="item_001",
            question_text="Resonera om satsdelar.",
            points=2,
            criteria=(ExamNetExportChecklistCriterion(text="Rätt begrepp.", points=2),),
        ),
    )


def test_entries_name_questions_by_item_id_never_the_flat_sequence() -> None:
    """A part of three children before a loss item: entries carry item ids.

    The drawer keys the list label off the item id, so the row after the part
    reads the list label ("Fråga 2") rather than the flat sequence ("Fråga 4").
    """
    children = [
        _free_text_item(sequence=sequence, item_id=f"item_00{sequence}") for sequence in (1, 2, 3)
    ]
    loss = _free_text_item(
        sequence=4,
        item_id="item_004",
        points=2,
        criteria=(NativeExamCriterion(text="Rätt begrepp.", points=2),),
    )
    document = _with_parent(
        document_of((*children, loss)),
        tuple(child.item_id for child in children),
    )

    entries = native_exam_export_checklist(document)

    assert [entry.item_id for entry in entries] == ["item_004"]


def test_child_loss_names_the_child_item_id() -> None:
    """A loss on a part child carries the child's id for its "1b" list label."""
    children = [
        _free_text_item(sequence=sequence, item_id=f"item_00{sequence}") for sequence in (1, 2)
    ]
    loss = _free_text_item(
        sequence=3,
        item_id="item_003",
        printed_label="c",
        points=2,
        criteria=(NativeExamCriterion(text="Rätt begrepp.", points=2),),
    )
    document = _with_parent(
        document_of((*children, loss)),
        tuple(child.item_id for child in (*children, loss)),
    )

    entries = native_exam_export_checklist(document)

    assert [entry.item_id for entry in entries] == ["item_003"]


@pytest.mark.parametrize("shared_parent", [False, True])
def test_uneven_gap_points_list_the_rounded_gap_value(shared_parent: bool) -> None:
    uneven = _gap_fill_item(sequence=1, item_id="item_001", points=5, gaps=3)
    if shared_parent:
        filler = _multiple_response_item(sequence=2, item_id="item_002", points=4, correct=2)
        document = _with_parent(document_of((uneven, filler)), (uneven.item_id, filler.item_id))
    else:
        document = document_of((uneven,))

    entries = native_exam_export_checklist(document)

    assert entries == (
        ExamNetExportChecklistRoundedGaps(
            item_id="item_001",
            question_text="Lucka 1: [___] Lucka 2: [___] Lucka 3: [___]",
            points=5,
            gap_points=1.66,
        ),
    )


def test_even_gap_points_list_nothing() -> None:
    item = _gap_fill_item(points=4, gaps=2)

    assert native_exam_export_checklist(document_of((item,))) == ()


def test_gap_share_floored_to_zero_lists_the_rounded_value() -> None:
    item = _gap_fill_item(points=0.01, gaps=2)

    entries = native_exam_export_checklist(document_of((item,)))

    assert entries == (
        ExamNetExportChecklistRoundedGaps(
            item_id="item_001",
            question_text="Lucka 1: [___] Lucka 2: [___]",
            points=0.01,
            gap_points=0,
        ),
    )


def test_gap_share_floored_to_zero_writes_no_gap_mapping() -> None:
    """The zero case is the writer's own mechanics: no mapping reaches the package."""

    item = _gap_fill_item(points=0.01, gaps=2)
    (qti_item,) = native_exam_to_examnet_qti_items(document_of((item,)))

    assert qti_item.interaction_type is ExamNetQtiInteractionType.GAP_FILL
    assert gap_point_values(qti_item) is None
    root = ElementTree.fromstring(serialize_qti_assessment_item(qti_item))
    assert root.find(f".//{{{QTI_NAMESPACE}}}qti-mapping") is None
    assert list(root.iter(f"{{{QTI_NAMESPACE}}}qti-map-entry")) == []


def test_question_text_is_the_start_of_the_question_text() -> None:
    long_text = "Förklara sambandet mellan satsdelarna och " + " ".join(
        f"ledtråd{index}" for index in range(1, 40)
    )
    item = _free_text_item(
        points=1, criteria=(NativeExamCriterion(text="Ett svar.", points=1),), text=long_text
    )

    (entry,) = native_exam_export_checklist(document_of((item,)))

    assert isinstance(entry, ExamNetExportChecklistFreeTextCriteria)
    assert entry.question_text.endswith("…")
    assert len(entry.question_text) <= 140
    assert long_text.startswith(entry.question_text.removesuffix("…").rstrip())


def test_export_without_losses_lists_nothing() -> None:
    document = document_of(
        (
            _gap_fill_item(sequence=1, item_id="item_001", points=4, gaps=2),
            _multiple_response_item(sequence=2, item_id="item_002", points=4, correct=2),
            _free_text_item(sequence=3, item_id="item_003", points=2),
        )
    )

    assert native_exam_export_checklist(document) == ()


def test_entries_stand_in_document_order() -> None:
    criteria_item = _free_text_item(
        sequence=1,
        item_id="item_001",
        points=2,
        criteria=(NativeExamCriterion(text="Rätt begrepp.", points=2),),
    )
    uneven_gaps = _gap_fill_item(sequence=2, item_id="item_002", points=5, gaps=3)
    document = document_of((criteria_item, uneven_gaps))

    entries = native_exam_export_checklist(document)

    assert [type(entry) for entry in entries] == [
        ExamNetExportChecklistFreeTextCriteria,
        ExamNetExportChecklistRoundedGaps,
    ]
    assert [entry.item_id for entry in entries] == ["item_001", "item_002"]
