"""Ordering export proof: print-order choices, key-order response, all-or-nothing scoring."""

import io
import zipfile
from dataclasses import replace
from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiPackageStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_admissibility import (
    blocking_errors,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_package import (
    build_examnet_qti_package_plan,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import qti_tag
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_validation import (
    build_examnet_qti_validation_report,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_export_checklist import (
    native_exam_export_checklist,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from tests.unit.domain.curated_apps.exam_workspace.examnet_qti_export_test_support import (
    document_of,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_ordering_item,
)

STEPS = ("Inledning", "Tes", "Argument", "Slutsats")
# Key order is choice_001..choice_004; the saved print order is not the key.
PRINT_ORDER = ("choice_003", "choice_001", "choice_004", "choice_002")
KEY_ORDER = ["choice_001", "choice_002", "choice_003", "choice_004"]


def _ordering_document(points: int | float = 1):
    return document_of((make_ordering_item(steps=STEPS, print_order=PRINT_ORDER, points=points),))


def _item_root(points: int | float = 1) -> ElementTree.Element:
    (qti,) = native_exam_to_examnet_qti_items(_ordering_document(points))
    return ElementTree.fromstring(serialize_qti_assessment_item(qti))


def test_choices_follow_print_order_and_correct_response_follows_key_order() -> None:
    root = _item_root()
    (interaction,) = root.iter(qti_tag("qti-order-interaction"))
    assert "shuffle" not in interaction.attrib
    assert interaction.find(qti_tag("qti-prompt")) is not None
    choices = interaction.findall(qti_tag("qti-simple-choice"))
    assert [c.attrib["identifier"] for c in choices] == list(PRINT_ORDER)
    assert ["".join(c.itertext()).strip() for c in choices] == [
        STEPS[2],
        STEPS[0],
        STEPS[3],
        STEPS[1],
    ]
    (declaration,) = root.iter(qti_tag("qti-response-declaration"))
    assert declaration.attrib["cardinality"] == "ordered"
    assert declaration.attrib["base-type"] == "identifier"
    assert declaration.attrib["identifier"] == interaction.attrib["response-identifier"]
    values = declaration.findall(f"{qti_tag('qti-correct-response')}/{qti_tag('qti-value')}")
    assert [v.text for v in values] == KEY_ORDER


@pytest.mark.parametrize("points", [1, 3, 2.5])
def test_scoring_is_all_or_nothing_for_the_full_points_and_never_mapped(
    points: int | float,
) -> None:
    root = _item_root(points)
    assert list(root.iter(qti_tag("qti-mapping"))) == []
    assert list(root.iter(qti_tag("qti-map-entry"))) == []
    assert list(root.iter(qti_tag("qti-map-response"))) == []
    processing = root.findall(qti_tag("qti-response-processing"))
    assert len(processing) == 1
    assert "template" not in processing[0].attrib
    conditions = processing[0].findall(qti_tag("qti-response-condition"))
    assert len(conditions) == 1
    response_if = conditions[0].find(qti_tag("qti-response-if"))
    assert response_if is not None
    match = response_if.find(qti_tag("qti-match"))
    assert match is not None
    assert match.find(qti_tag("qti-correct")) is not None
    added = [float(value.text or "") for value in response_if.iter(qti_tag("qti-base-value"))]
    assert added == [float(points)]
    max_score = next(
        outcome
        for outcome in root.findall(qti_tag("qti-outcome-declaration"))
        if outcome.attrib["identifier"] == "MAXSCORE"
    )
    default = max_score.find(f"{qti_tag('qti-default-value')}/{qti_tag('qti-value')}")
    assert default is not None
    assert float(default.text or "") == float(points)


def test_package_validator_reports_no_errors_for_an_ordering_item() -> None:
    items = native_exam_to_examnet_qti_items(_ordering_document(3))
    plan = build_examnet_qti_package_plan(package_name="ordering", items=items)
    assert plan.status is ExamNetQtiPackageStatus.PASSED, plan.warnings
    package = ExamNetQtiPackageWriter().build_package_bytes(plan)
    report = build_examnet_qti_validation_report(
        plan=plan, package_filename="ordering.zip", package_bytes=package
    )
    assert report.errors == ()
    local = report.validator_results[0]
    assert local.status.value == "passed", local.message
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        item_names = [n for n in archive.namelist() if n.startswith("items/")]
        assert len(item_names) == 1
        assert b"qti-order-interaction" in archive.read(item_names[0])
    assert plan.manual_follow_ups == ()


def _qti_item() -> ExamNetQtiItem:
    (qti,) = native_exam_to_examnet_qti_items(_ordering_document(3))
    return qti


def test_admissibility_refuses_a_one_step_ordering() -> None:
    qti = _qti_item()
    one_step = replace(qti, choices=qti.choices[:1], correct_choice_identifiers=("choice_001",))
    assert blocking_errors((one_step,))


def test_admissibility_refuses_a_correct_order_that_is_not_a_permutation() -> None:
    qti = _qti_item()
    assert not blocking_errors((qti,))
    for bad in (
        ("choice_001", "choice_002", "choice_003"),
        ("choice_001", "choice_001", "choice_002", "choice_003"),
        ("choice_001", "choice_002", "choice_003", "choice_009"),
        (),
    ):
        assert blocking_errors((replace(qti, correct_choice_identifiers=bad),)), bad


def test_admissibility_refuses_duplicate_step_identifiers() -> None:
    qti = _qti_item()
    duplicated = replace(
        qti,
        choices=(*qti.choices[:3], ExamNetQtiChoice(qti.choices[0].identifier, "Kopia")),
    )
    assert blocking_errors((duplicated,))


def test_ordering_interaction_type_is_mapped_from_the_native_kind() -> None:
    assert _qti_item().interaction_type is ExamNetQtiInteractionType.ORDERING


def test_checklist_lists_no_all_or_nothing_loss_for_a_three_point_ordering() -> None:
    assert native_exam_export_checklist(_ordering_document(3)) == ()
