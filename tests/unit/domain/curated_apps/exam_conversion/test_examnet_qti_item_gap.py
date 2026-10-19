"""Gap-interaction tests for the Exam.net QTI item reader.

Purpose:
    Prove that `examnet_qti_gap_item_reader` inverts the writer's gap-fill
    and inline-choice layouts through `read_examnet_qti_item`, and that gap
    layouts the import does not map become documented unsupported items.

Relationships:
    - Split from `test_examnet_qti_item_reader.py`; shared builders live in
      `examnet_qti_reader_test_support` and are imported, never copied.
"""

from __future__ import annotations

from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiTextEntryGap,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import QTI_NAMESPACE
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeGap,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    item_round_trip as _round_trip,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    item_unsupported as _unsupported,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    xml_body as _body,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    xml_declaration as _declaration,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    xml_max_score as _max_score,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    xml_root as _root,
)
from tests.unit.domain.curated_apps.exam_workspace.examnet_qti_export_test_support import (
    review_complete,
)

pytestmark = pytest.mark.unit

_QTI = f"{{{QTI_NAMESPACE}}}"


def _gap_fill_item(*, points: int | float | None, accepted: tuple[str, ...]) -> NativeExamItem:
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.GAP_FILL,
        body=(
            NativeParagraph(
                heading_level=None,
                segments=(
                    NativeTextSegment(text="Frastyp: ", marks=()),
                    NativeGapSegment(gap_id="gap_001"),
                ),
            ),
        ),
        points=points,
        gaps=(NativeGap(gap_id="gap_001", accepted_values=accepted),),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED),
        review=review_complete(),
    )


@pytest.mark.parametrize("points", [2, None])
def test_gap_fill_reads_every_accepted_value_with_and_without_points(
    points: int | float | None,
) -> None:
    item = _gap_fill_item(points=points, accepted=("NF", "nf"))

    exported, read = _round_trip(item)

    assert exported.max_score == points
    # The writer coerces an inadmissible absent score to "0", which reads back
    # as a stated zero (review 596c1654 F5); the real export route blocks such
    # items with the missing_points blocker instead.
    assert read.max_score == (0 if points is None else points)
    assert read.text_entry_gaps == (
        ExamNetQtiTextEntryGap(
            response_identifier=exported.text_entry_gaps[0].response_identifier,
            label="",
            accepted_values=("NF", "nf"),
        ),
    )


def test_mixed_text_entry_and_inline_choice_is_unsupported() -> None:
    root = _root()
    _declaration(root, identifier="TEXT")
    _declaration(root, identifier="INLINE", base_type="identifier", correct=("choice_001",))
    body = _body(root)
    paragraph = ElementTree.SubElement(body, f"{_QTI}p")
    ElementTree.SubElement(
        paragraph, f"{_QTI}qti-text-entry-interaction", {"response-identifier": "TEXT"}
    )
    inline = ElementTree.SubElement(
        paragraph,
        f"{_QTI}qti-inline-choice-interaction",
        {"response-identifier": "INLINE"},
    )
    ElementTree.SubElement(inline, f"{_QTI}qti-inline-choice", {"identifier": "choice_001"})

    _unsupported(root)


def test_inline_choice_without_a_correct_value_is_unsupported() -> None:
    root = _root()
    _declaration(root, identifier="INLINE", base_type="identifier")
    _max_score(root)
    body = _body(root)
    paragraph = ElementTree.SubElement(body, f"{_QTI}p")
    inline = ElementTree.SubElement(
        paragraph,
        f"{_QTI}qti-inline-choice-interaction",
        {"response-identifier": "INLINE"},
    )
    ElementTree.SubElement(inline, f"{_QTI}qti-inline-choice", {"identifier": "choice_001"})

    _unsupported(root)


def test_inline_choice_with_a_correct_value_outside_its_options_is_unsupported() -> None:
    root = _root()
    _declaration(root, identifier="INLINE", base_type="identifier", correct=("choice_404",))
    _max_score(root)
    body = _body(root)
    paragraph = ElementTree.SubElement(body, f"{_QTI}p")
    inline = ElementTree.SubElement(
        paragraph,
        f"{_QTI}qti-inline-choice-interaction",
        {"response-identifier": "INLINE"},
    )
    ElementTree.SubElement(inline, f"{_QTI}qti-inline-choice", {"identifier": "choice_001"})

    _unsupported(root)


def test_a_response_identifier_without_a_declaration_is_unsupported() -> None:
    root = _root()
    _max_score(root)
    body = _body(root)
    paragraph = ElementTree.SubElement(body, f"{_QTI}p")
    ElementTree.SubElement(
        paragraph,
        f"{_QTI}qti-text-entry-interaction",
        {"response-identifier": "MISSING"},
    )

    _unsupported(root)
