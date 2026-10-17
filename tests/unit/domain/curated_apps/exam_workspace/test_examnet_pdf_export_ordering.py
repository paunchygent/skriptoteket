"""Ordering items print a number box per step in the saved print order, key in a facit line."""

import re

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfStatus,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_pdf_export import (
    native_exam_to_pdf_document,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_ordering_item,
    make_paragraph,
)

_STEP = re.compile(r'<p class="ordering-step"><span class="number-box"></span> ([^<]*)</p>')
_FACIT = re.compile(r'<p class="answer-key">([^<:]*): ([^<]*)</p>')


def _html(*steps: str, english: bool = False, **kwargs: object) -> str:
    item = make_ordering_item(**({"steps": steps} if steps else {}), **kwargs)  # type: ignore[arg-type]
    if english:
        item = item.model_copy(
            update={"body": (make_paragraph("Put the steps of what is an essay in order."),)}
        )
    result = native_exam_to_pdf_document(make_document(item))
    assert result.status is DigiExamExamNetPdfStatus.SUCCESS, result.warnings
    return result.html


def test_steps_print_in_print_order_with_one_empty_box_each() -> None:
    html = _html()
    assert _STEP.findall(html) == ["Avslutning", "Motargument", "Argument", "Tes"]
    assert html.count('class="number-box"') == 4


def test_student_part_has_no_key_numbers_and_facit_is_separate() -> None:
    html = _html(english=True)
    student_part = html.split('<p class="answer-key">')[0]
    assert not re.search(r"(Tes|Argument|Motargument|Avslutning) \d", student_part)
    ((label, line),) = _FACIT.findall(html)
    assert line == "Avslutning 4; Motargument 3; Argument 2; Tes 1"
    assert label == "Correct order"


def test_swedish_exam_labels_the_facit_in_swedish() -> None:
    ((label, _line),) = _FACIT.findall(_html())
    assert label == "Rätt ordning"


def test_custom_print_order_and_points_do_not_crash() -> None:
    html = _html(print_order=("choice_002", "choice_004", "choice_001", "choice_003"), points=2.5)
    assert _STEP.findall(html) == ["Argument", "Avslutning", "Tes", "Motargument"]
    assert _FACIT.findall(html)[0][1] == "Argument 2; Avslutning 4; Tes 1; Motargument 3"


def test_single_step_renders_without_error() -> None:
    item = make_ordering_item(steps=("Ensam",), print_order=("choice_001",))
    result = native_exam_to_pdf_document(make_document(item))
    assert result.status is DigiExamExamNetPdfStatus.SUCCESS
    assert _FACIT.findall(result.html)[0][1] == "Ensam 1"
