"""Checklist agreement with the QTI writer predicates on the recorded corpus (Q15-Q17).

The checklist may only list what the writer's own scoring predicates say the package
loses, on the real recorded exams: no listed leaf the writer scores differently, and
no writer loss the checklist omits. The rounded and criteria entries are re-read from
the serialized package, so the numbers come from the XML the export ships.
"""

from decimal import Decimal
from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_xml import (
    QTI_NAMESPACE,
    emits_all_or_nothing,
    gap_point_values,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_export_checklist import (
    ExamNetExportChecklistFreeTextCriteria,
    ExamNetExportChecklistRoundedGaps,
    native_exam_export_checklist,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from tests.unit.domain.curated_apps.exam_workspace.recorded_native_exam_support import (
    parent_over,
    recorded_document,
    recorded_items,
)

_LOSS_EXAMS = (
    "svenska_2_grammatik_omprov_variant_1_med_facit",
    "svenska_2_grammatik_omprov_variant_2_med_facit",
    "svenska_2_kursavslutande_prov_med_facit",
)
_MULTIPLE_RESPONSE_EXAM = "metodprov_vetenskaplig_metod_med_facit"

_Loss = tuple[str, int | float | None]


def _leaves_by_sequence(document: NativeExamDocument) -> dict[int, ExamNetQtiItem]:
    leaves: dict[int, ExamNetQtiItem] = {}
    for qti_item in native_exam_to_examnet_qti_items(document):
        for leaf in qti_item.children or (qti_item,):
            leaves[leaf.sequence] = leaf
    return leaves


def _writer_rounded_gap_points(qti_item: ExamNetQtiItem) -> int | float | None:
    if not qti_item.text_entry_gaps or qti_item.max_score is None:
        return None
    rounded = gap_point_values(qti_item)
    if rounded is None:
        return 0
    per_gap = Decimal(rounded[0])
    if per_gap * len(qti_item.text_entry_gaps) == Decimal(str(qti_item.max_score)):
        return None
    return int(per_gap) if per_gap == per_gap.to_integral_value() else float(per_gap)


def _expected_losses(document: NativeExamDocument) -> dict[int, _Loss]:
    """Every loss exactly as the writer predicates decide it, keyed by leaf sequence."""

    native_by_sequence = {item.sequence: item for item in document.items}
    losses: dict[int, _Loss] = {}
    for qti_item in native_exam_to_examnet_qti_items(document):
        for leaf in qti_item.children or (qti_item,):
            native_item = native_by_sequence[leaf.sequence]
            if leaf.interaction_type is ExamNetQtiInteractionType.FREE_TEXT:
                if leaf.free_text_criterion_points is not None and native_item.criteria:
                    losses[leaf.sequence] = ("free_text_criteria", None)
            elif leaf.interaction_type is ExamNetQtiInteractionType.GAP_FILL:
                gap_points = _writer_rounded_gap_points(leaf)
                if gap_points is not None:
                    losses[leaf.sequence] = ("rounded_gaps", gap_points)
            elif qti_item.children and emits_all_or_nothing(leaf):
                if leaf.max_score is not None and leaf.max_score >= 2:
                    losses[leaf.sequence] = ("all_or_nothing", None)
    return losses


def _actual_losses(
    document: NativeExamDocument,
) -> dict[int, _Loss]:
    sequence_by_item_id = {item.item_id: item.sequence for item in document.items}
    losses: dict[int, _Loss] = {}
    for entry in native_exam_export_checklist(document):
        if isinstance(entry, ExamNetExportChecklistFreeTextCriteria):
            losses[sequence_by_item_id[entry.item_id]] = ("free_text_criteria", None)
        elif isinstance(entry, ExamNetExportChecklistRoundedGaps):
            losses[sequence_by_item_id[entry.item_id]] = ("rounded_gaps", entry.gap_points)
        else:
            losses[sequence_by_item_id[entry.item_id]] = ("all_or_nothing", None)
    return losses


@pytest.mark.parametrize("exam", _LOSS_EXAMS)
def test_recorded_loss_exam_agrees_leaf_for_leaf(exam: str) -> None:
    document = recorded_document(items=recorded_items(exam))

    expected = _expected_losses(document)

    assert expected, "recording must exercise real losses"
    assert _actual_losses(document) == expected


@pytest.mark.parametrize("exam", _LOSS_EXAMS)
def test_shared_parent_grouping_agrees_leaf_for_leaf(exam: str) -> None:
    items = recorded_items(exam)
    numbers = tuple(item.sequence for item in items[:4])
    document = recorded_document(
        items=items,
        parents=(parent_over("parent_001", "Answer every question.", *numbers),),
    )

    assert _actual_losses(document) == _expected_losses(document)


@pytest.mark.parametrize("exam", _LOSS_EXAMS)
def test_rounded_entries_re_read_the_serialized_gap_mappings(exam: str) -> None:
    document = recorded_document(items=recorded_items(exam))
    leaves = _leaves_by_sequence(document)
    entries = [
        entry
        for entry in native_exam_export_checklist(document)
        if isinstance(entry, ExamNetExportChecklistRoundedGaps)
    ]

    if not entries:
        pytest.skip(f"{exam} has no rounded gap loss")
    sequence_by_item_id = {item.item_id: item.sequence for item in document.items}
    for entry in entries:
        leaf = leaves[sequence_by_item_id[entry.item_id]]
        root = ElementTree.fromstring(serialize_qti_assessment_item(leaf))
        values = [
            element.attrib["mapped-value"]
            for element in root.iter(f"{{{QTI_NAMESPACE}}}qti-map-entry")
        ]
        assert len(values) == sum(len(gap.accepted_values) for gap in leaf.text_entry_gaps)
        assert {Decimal(value) for value in values} == {Decimal(str(entry.gap_points))}


def test_loss_exams_exercise_both_rounded_gaps_and_free_text_criteria() -> None:
    kinds = {
        type(entry)
        for exam in _LOSS_EXAMS
        for entry in native_exam_export_checklist(recorded_document(items=recorded_items(exam)))
    }

    assert kinds == {
        ExamNetExportChecklistRoundedGaps,
        ExamNetExportChecklistFreeTextCriteria,
    }


@pytest.mark.parametrize("exam", _LOSS_EXAMS)
def test_free_text_entries_re_read_the_serialized_criterion_rows(exam: str) -> None:
    document = recorded_document(items=recorded_items(exam))
    leaves = _leaves_by_sequence(document)
    entries = [
        entry
        for entry in native_exam_export_checklist(document)
        if isinstance(entry, ExamNetExportChecklistFreeTextCriteria)
    ]

    sequence_by_item_id = {item.item_id: item.sequence for item in document.items}
    for entry in entries:
        leaf = leaves[sequence_by_item_id[entry.item_id]]
        root = ElementTree.fromstring(serialize_qti_assessment_item(leaf))
        mapping = root.find(f".//{{{QTI_NAMESPACE}}}qti-mapping")
        assert mapping is not None
        rows = mapping.findall(f"{{{QTI_NAMESPACE}}}qti-map-entry")
        assert len(rows) == sum(criterion.points for criterion in entry.criteria)
        package_xml = ElementTree.tostring(root, encoding="unicode")
        for criterion in entry.criteria:
            assert criterion.text not in package_xml


def test_edited_recorded_multiple_response_agrees_as_all_or_nothing() -> None:
    """A recorded multiple-response question, its points re-pointed unevenly (3.01).

    The corpus's own multiple-response items divide evenly over their correct
    answers, so the edit is what exercises the all-or-nothing agreement through the
    real serializer.
    """

    items = recorded_items(_MULTIPLE_RESPONSE_EXAM)
    multiple = next(item for item in items if item.kind.value == "multiple_response")
    edited = tuple(
        item.model_copy(update={"points": 3.01}) if item.sequence == multiple.sequence else item
        for item in items
    )
    document = recorded_document(
        items=edited,
        parents=(
            parent_over(
                "parent_001", "Answer every question.", multiple.sequence, multiple.sequence + 1
            ),
        ),
    )

    assert _actual_losses(document) == _expected_losses(document)
    leaf = _leaves_by_sequence(document)[multiple.sequence]
    assert emits_all_or_nothing(leaf)
    root = ElementTree.fromstring(serialize_qti_assessment_item(leaf))
    base_values = [element.text for element in root.iter(f"{{{QTI_NAMESPACE}}}qti-base-value")]
    assert "3.01" in base_values
    assert root.find(f".//{{{QTI_NAMESPACE}}}qti-mapping") is None
