"""Tests for the keyed QTI Exam.net QTI package contract.

Purpose:
    Prove deterministic QTI 3.0 sample package generation, image packaging,
    unsupported-resource reporting, assessment-test manifest wiring, and
    DigiExam IR adapter alignment, ported from Sir Convert-a-Lot at revision
    41be61a6.

Relationships:
    - Exercises the exam-conversion QTI package planning, manifest, and
      deterministic byte materialization without service routes or UI behavior.
"""

from __future__ import annotations

import hashlib
import zipfile
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_dxe_parser import DigiExamDxeParser
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_qti_adapter import (
    build_examnet_qti_items_from_digiexam_ir,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ir_contracts import (
    build_digiexam_intermediate_exam,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiInteractionType,
    ExamNetQtiManualFollowUpReason,
    ExamNetQtiPackageStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_manifest import IMSCP_NAMESPACE
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_package import (
    build_examnet_qti_package_plan,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_xml import QTI_NAMESPACE
from skriptoteket.domain.errors import DomainError, ErrorCode
from tests.fixtures.exam_conversion_samples import (
    examnet_qti_keyed_samples,
    examnet_qti_manual_unkeyed_samples,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_test_support import (
    build_examnet_qti_zip_bytes,
    first_manual_follow_up,
    item_body_paragraphs,
    json_string,
    keyed_sample,
    read_report,
    write_sample,
)

pytestmark = pytest.mark.unit


def test_sample_packages_are_deterministic(tmp_path: Path) -> None:
    for sample in examnet_qti_keyed_samples():
        first = write_sample(sample, tmp_path / "first")
        second = write_sample(sample, tmp_path / "second")

        first_report = read_report(first / sample.report_filename)
        second_report = read_report(second / sample.report_filename)

        assert json_string(first_report, "package_status") == "passed"
        assert json_string(first_report, "package_sha256") == json_string(
            second_report,
            "package_sha256",
        )
        assert _validator_statuses(first_report) == [
            "passed",
            "external_validator_unavailable",
            "not_run",
        ]
        assert (first / sample.package_filename).read_bytes() == (
            second / sample.package_filename
        ).read_bytes()


def test_image_packages_include_manifest_hrefs_and_resolved_item_images(tmp_path: Path) -> None:
    for sample_name in ("image-single-choice-mcq", "image-free-text"):
        sample_dir = write_sample(keyed_sample(sample_name), tmp_path / sample_name)
        with zipfile.ZipFile(sample_dir / "qti-package.zip") as archive:
            names = set(archive.namelist())
            assert "imsmanifest.xml" in names
            image_names = {name for name in names if name.startswith("items/images/")}
            assert image_names == {"items/images/item_001-image_001.png"}
            assert not any(name.startswith("resources/") for name in names)
            manifest = archive.read("imsmanifest.xml").decode("utf-8")
            item_xml = archive.read("items/item_001.xml").decode("utf-8")

        assert '<file href="items/images/item_001-image_001.png"' in manifest
        assert 'src="images/item_001-image_001.png"' in item_xml
        assert "resources/" not in manifest
        assert "resources/" not in item_xml
        item = ElementTree.fromstring(item_xml)
        prompt_images = item.findall(f".//{{{QTI_NAMESPACE}}}qti-prompt/{{{QTI_NAMESPACE}}}img")
        assert [image.attrib["src"] for image in prompt_images] == ["images/item_001-image_001.png"]
        assert item_body_paragraphs(item) == []
        report = read_report(sample_dir / "qti-validation-report.json")
        assert json_string(report, "package_sha256") == _sha256(sample_dir / "qti-package.zip")


def test_unsupported_resources_are_omitted_and_reported(tmp_path: Path) -> None:
    sample_dir = write_sample(keyed_sample("unsupported-resource-omission"), tmp_path)
    report = read_report(sample_dir / "qti-validation-report.json")

    with zipfile.ZipFile(sample_dir / "qti-package.zip") as archive:
        names = archive.namelist()

    assert all(not name.endswith((".mp3", ".pdf", ".ggb")) for name in names)
    follow_up = first_manual_follow_up(report)
    assert json_string(follow_up, "reason_code") == (
        ExamNetQtiManualFollowUpReason.UNSUPPORTED_EXAMNET_QTI_RESOURCE
    )
    assert "teacher-audio.mp3" in json_string(follow_up, "message")


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_blank_assessment_title_is_refused_not_replaced_by_the_package_name(blank: str) -> None:
    sample = keyed_sample("free-text")

    with pytest.raises(DomainError) as refusal:
        build_examnet_qti_package_plan(
            package_name=sample.name, assessment_title=blank, items=sample.items
        )

    assert refusal.value.code is ErrorCode.VALIDATION_ERROR
    assert "title" in refusal.value.message


def test_assessment_title_names_the_manifest_independent_of_the_package_name() -> None:
    sample = keyed_sample("free-text")

    plan = build_examnet_qti_package_plan(
        package_name="the-file", assessment_title="The exam", items=sample.items
    )

    manifest = next(file for file in plan.files if file.relative_path == "imsmanifest.xml")
    assert b"The exam" in manifest.payload
    assert b"the-file" not in manifest.payload


def test_all_sample_packages_wire_assessment_test_into_manifest() -> None:
    for sample in (*examnet_qti_keyed_samples(), *examnet_qti_manual_unkeyed_samples()):
        plan = build_examnet_qti_package_plan(
            package_name=sample.name, assessment_title=sample.name, items=sample.items
        )
        if plan.status != ExamNetQtiPackageStatus.PASSED:
            continue
        zip_bytes = build_examnet_qti_zip_bytes(plan)

        with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
            names = set(archive.namelist())
            manifest = ElementTree.fromstring(archive.read("imsmanifest.xml"))
            assessment = ElementTree.fromstring(archive.read("assessment.xml"))

        assert "assessment.xml" in names
        resources = manifest.findall(f".//{{{IMSCP_NAMESPACE}}}resource")
        test_resources = [
            resource for resource in resources if resource.attrib["type"] == "imsqti_test_xmlv3p0"
        ]
        assert len(test_resources) == 1
        assert test_resources[0].attrib["identifier"] == "res_test"
        assert test_resources[0].attrib["href"] == "assessment.xml"
        file_hrefs = {
            file.attrib["href"] for file in test_resources[0].findall(f"{{{IMSCP_NAMESPACE}}}file")
        }
        assert file_hrefs == {"assessment.xml"}
        item_identifiers = {
            resource.attrib["identifier"]
            for resource in resources
            if resource.attrib["type"] == "imsqti_item_xmlv3p0"
        }
        dependency_refs = {
            dependency.attrib["identifierref"]
            for dependency in test_resources[0].findall(f"{{{IMSCP_NAMESPACE}}}dependency")
        }
        assert item_identifiers
        assert dependency_refs == item_identifiers
        assert assessment.tag == f"{{{QTI_NAMESPACE}}}qti-assessment-test"
        item_refs = assessment.findall(f".//{{{QTI_NAMESPACE}}}qti-assessment-item-ref")
        assert item_refs
        assert all(item_ref.attrib["href"] in names for item_ref in item_refs)


def test_digiexam_ir_adapter_feeds_reusable_qti_package_plan() -> None:
    parse_result = DigiExamDxeParser().parse_payload(
        _digiexam_renderable_payload(),
        filename="qti-adapter.dxe",
    )
    exam = build_digiexam_intermediate_exam(parse_result)

    adapter_result = build_examnet_qti_items_from_digiexam_ir(exam)
    plan = build_examnet_qti_package_plan(
        package_name="digiexam-adapter",
        assessment_title="digiexam-adapter",
        items=adapter_result.items,
    )
    zip_bytes = build_examnet_qti_zip_bytes(plan)

    assert [item.interaction_type for item in adapter_result.items] == [
        ExamNetQtiInteractionType.FREE_TEXT,
        ExamNetQtiInteractionType.SINGLE_CHOICE,
        ExamNetQtiInteractionType.MULTIPLE_RESPONSE,
    ]
    assert adapter_result.manual_follow_ups == ()
    assert plan.status == ExamNetQtiPackageStatus.PASSED
    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        item_xml = archive.read("items/item_001.xml") + archive.read("items/item_002.xml")
    assert b"choice_002" in item_xml
    assert b"qti-extended-text-interaction" in item_xml


def _validator_statuses(report: dict[str, object]) -> list[str]:
    value = report["validator_results"]
    assert isinstance(value, list)
    statuses: list[str] = []
    for entry in value:
        assert isinstance(entry, dict)
        status = entry.get("status")
        assert isinstance(status, str)
        statuses.append(status)
    return statuses


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digiexam_renderable_payload() -> dict[str, object]:
    return {
        "exams": [
            {
                "questions": [
                    {
                        "id": 1,
                        "title": "Essay",
                        "about": "",
                        "bodyHTML": "<p>Explain the water cycle.</p>",
                        "images": [],
                        "maxScore": 3,
                        "type": 0,
                    },
                    {
                        "id": 2,
                        "title": "Single",
                        "about": "",
                        "bodyHTML": "<p>Choose the Greek letter.</p>",
                        "images": [],
                        "maxScore": 2,
                        "type": 1,
                        "alternatives": [
                            {"id": 1, "title": "Alpha", "about": "", "right": False},
                            {"id": 2, "title": "Beta", "about": "", "right": True},
                        ],
                    },
                    {
                        "id": 3,
                        "title": "Multiple",
                        "about": "",
                        "bodyHTML": "<p>Choose the ordinal words.</p>",
                        "images": [],
                        "maxScore": 4,
                        "type": 2,
                        "alternatives": [
                            {"id": 1, "title": "First", "about": "", "right": True},
                            {"id": 2, "title": "Between", "about": "", "right": False},
                            {"id": 3, "title": "Third", "about": "", "right": True},
                        ],
                    },
                ]
            }
        ]
    }
