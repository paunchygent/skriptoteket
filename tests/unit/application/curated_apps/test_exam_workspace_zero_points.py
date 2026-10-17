"""Zero is a real score, not missing data; invalid numbers remain rejected."""

import json
from decimal import Decimal
from io import BytesIO
from uuid import uuid4
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import pytest
from pydantic import ValidationError

from skriptoteket.application.curated_apps.exam_workspace_exports import (
    build_native_examnet_qti_package,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_export_header import (
    exam_export_header_lines,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_export_checklist import (
    native_exam_export_checklist,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_pdf_export import (
    native_exam_to_pdf_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    native_export_blockers,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
    NativeGap,
    NativeItemReview,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_writer import (  # noqa: E501
    ExamWorkspaceDocxWriter,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import plain_body
from tests.unit.domain.curated_apps.exam_workspace.native_matching_test_support import matching_item


def _item(kind="single_choice", points=0):
    if kind == "matching":
        return matching_item(tick_points=Decimal("0"), points=points)
    data = dict(
        item_id="item_001",
        sequence=1,
        kind=kind,
        points=points,
        body=plain_body("Nollpoängsfråga"),
        review=NativeItemReview(state="review_complete", parse_origin="deterministic"),
    )
    if kind in {"single_choice", "multiple_response"}:
        data.update(
            choices=(
                NativeChoice(choice_id="choice_001", body=plain_body("Rätt")),
                NativeChoice(choice_id="choice_002", body=plain_body("Fel")),
            ),
            answer_key=NativeAnswerKey(
                origin="source_provided", correct_choice_ids=("choice_001",)
            ),
        )
    elif kind == "gap_fill":
        data.update(
            body=(
                NativeParagraph(heading_level=None, segments=(NativeGapSegment(gap_id="gap_001"),)),
            ),
            gaps=(NativeGap(gap_id="gap_001", accepted_values=("rätt",)),),
            answer_key=NativeAnswerKey(origin="source_provided"),
        )
    else:
        data["answer_key"] = NativeAnswerKey(origin="not_applicable")
    return NativeExamItem.model_validate(data)


def _document(item):
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Nollpoängsprov",
        items=(item,),
        origin=NativeExamDocumentOrigin(kind="created"),
    )


@pytest.mark.parametrize("value", [0, 0.0, 1, 10, 0.25])
def test_nonnegative_finite_points_are_preserved_exactly(value):
    item = _item(points=value)
    assert item.points == value
    assert NativeExamItem.model_validate_json(item.model_dump_json()).points == value


@pytest.mark.parametrize(
    "value", [-1, -0.1, float("nan"), float("inf"), float("-inf"), True, False, "0", "wrong"]
)
def test_negative_nonfinite_or_non_numeric_points_are_rejected(value):
    with pytest.raises(ValidationError):
        _item(points=value)


@pytest.mark.parametrize(
    "kind", ["single_choice", "multiple_response", "gap_fill", "free_text", "matching"]
)
def test_zero_point_questions_are_exportable_in_valid_qti_and_print_exports(kind):
    document = _document(_item(kind))
    assert native_export_blockers(document) == ()
    assert native_exam_export_checklist(document) == ()
    assert "Totalt: 0 poäng" in exam_export_header_lines(document)
    package, report = build_native_examnet_qti_package(
        document, package_name="zero", qti_writer=ExamNetQtiPackageWriter()
    )
    assert json.loads(report)["package_status"] == "passed"
    with ZipFile(BytesIO(package)) as archive:
        items = [
            name
            for name in archive.namelist()
            if name.startswith("items/") and name.endswith(".xml")
        ]
        assert len(items) == 1
        root = ET.fromstring(archive.read(items[0]))
        declarations = [node for node in root if node.tag.endswith("qti-outcome-declaration")]
        maximum = next(node for node in declarations if node.attrib["identifier"] == "MAXSCORE")
        values = [node.text for node in maximum.iter() if node.tag.endswith("qti-value")]
        assert values == ["0"]
        if kind in {"gap_fill", "matching"}:
            mappings = [node for node in root.iter() if node.tag.endswith("qti-map-entry")]
            assert mappings and all(float(node.attrib["mapped-value"]) == 0 for node in mappings)
    pdf = native_exam_to_pdf_document(document)
    assert pdf.status.value == "success"
    assert "Totalt: 0 poäng" in pdf.html
    docx = ExamWorkspaceDocxWriter().build_docx_bytes(document)
    with ZipFile(BytesIO(docx)) as archive:
        xml = ET.fromstring(archive.read("word/document.xml"))
        text = " ".join(node.text or "" for node in xml.iter() if node.tag.endswith("}t"))
    assert "Totalt: 0 poäng" in text


@pytest.mark.parametrize("points", [10, 100, 10.5])
def test_totals_do_not_trim_integer_zero_digits(points):
    assert f"Totalt: {str(points).replace('.', ',')} poäng" in exam_export_header_lines(
        _document(_item(points=points))
    )


@pytest.mark.parametrize("kind", ["free_text", "single_choice"])
@pytest.mark.parametrize("points", [10, 100])
def test_qti_score_declarations_and_mapping_do_not_drop_integer_zero_digits(kind, points):
    document = _document(_item(kind=kind, points=points))
    package, report = build_native_examnet_qti_package(
        document, package_name="integer", qti_writer=ExamNetQtiPackageWriter()
    )
    assert json.loads(report)["package_status"] == "passed"
    with ZipFile(BytesIO(package)) as archive:
        name = next(
            name
            for name in archive.namelist()
            if name.startswith("items/") and name.endswith(".xml")
        )
        root = ET.fromstring(archive.read(name))
    maximum = next(node for node in root if node.attrib.get("identifier") == "MAXSCORE")
    assert [node.text for node in maximum.iter() if node.tag.endswith("qti-value")] == [str(points)]
    if kind == "single_choice":
        mappings = [node for node in root.iter() if node.tag.endswith("qti-map-entry")]
        assert any(node.attrib["mapped-value"] == str(points) for node in mappings)


@pytest.mark.parametrize(
    "tick", [Decimal("-1"), Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity"), True]
)
def test_matching_rejects_negative_nonfinite_and_boolean_tick_points(tick):
    with pytest.raises(ValidationError):
        matching_item(tick_points=tick, points=0)


@pytest.mark.parametrize("tick,points", [(Decimal("0"), 1), (Decimal("1"), 0)])
def test_zero_does_not_disable_matching_points_product_invariant(tick, points):
    with pytest.raises(ValidationError):
        matching_item(tick_points=tick, points=points)
