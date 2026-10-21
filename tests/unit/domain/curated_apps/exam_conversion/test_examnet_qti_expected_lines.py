"""Focused tests for the QTI free-text answer box following the writing area (W2).

Purpose:
    Prove that a free-text item's ``expected-lines`` equals the question's
    writing lines instead of the fixed 8, that a free-text item without them
    fails closed, and that the DigiExam lane keeps the house default.

Relationships:
    - Exercises `domain.examnet_qti_xml` through `domain.examnet_qti_item_xml`.
    - Drives the native export producer.
"""

from __future__ import annotations

from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_xml import QTI_NAMESPACE
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import NativeAnswerKey
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from tests.unit.domain.curated_apps.exam_workspace.examnet_qti_export_test_support import (
    document_of,
    review_complete,
    text_body,
)

pytestmark = pytest.mark.unit


def _native_free_text(*, writing_lines: int) -> NativeExamItem:
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.FREE_TEXT,
        writing_lines=writing_lines,
        body=text_body("Resonera om satsdelar."),
        points=2,
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=review_complete(),
    )


def _extended_text(root: ElementTree.Element) -> ElementTree.Element:
    interaction = root.find(f".//{{{QTI_NAMESPACE}}}qti-extended-text-interaction")
    assert interaction is not None
    return interaction


@pytest.mark.parametrize("writing_lines", (3, 40))
def test_native_free_text_writing_lines_drive_expected_lines(writing_lines: int) -> None:
    (qti_item,) = native_exam_to_examnet_qti_items(
        document_of((_native_free_text(writing_lines=writing_lines),))
    )

    assert qti_item.expected_lines == writing_lines
    root = ElementTree.fromstring(serialize_qti_assessment_item(qti_item))
    assert _extended_text(root).attrib["expected-lines"] == str(writing_lines)


def test_three_line_free_text_never_keeps_the_fixed_eight() -> None:
    (qti_item,) = native_exam_to_examnet_qti_items(
        document_of((_native_free_text(writing_lines=3),))
    )
    xml = serialize_qti_assessment_item(qti_item).decode("utf-8")

    assert 'expected-lines="3"' in xml
    assert 'expected-lines="8"' not in xml


def test_free_text_without_expected_lines_fails_closed() -> None:
    item = ExamNetQtiItem(
        item_id="item_001",
        sequence=1,
        title="Fråga 1",
        interaction_type=ExamNetQtiInteractionType.FREE_TEXT,
        prompt_lines=("Resonera.",),
        max_score=1,
    )

    with pytest.raises(ValueError, match="need expected_lines"):
        serialize_qti_assessment_item(item)
