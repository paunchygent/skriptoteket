"""Shared builders for the Exam.net QTI package tests.

Purpose:
    Hold the sample-package writer, validation-report readers, and item-body
    helpers used by more than one Exam.net QTI package test module.

Relationships:
    - Used by the interaction, package, and admissibility test modules in this
      directory.
"""

from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiPackagePlan,
    ExamNetQtiPackageStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_package import (
    build_examnet_qti_package_plan,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_xml import QTI_NAMESPACE
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from tests.fixtures.exam_conversion_samples import (
    ExamNetQtiSamplePackage,
    examnet_qti_keyed_samples,
)

QTI_PACKAGE_WRITER = ExamNetQtiPackageWriter()


def build_examnet_qti_zip_bytes(plan: ExamNetQtiPackagePlan) -> bytes:
    return QTI_PACKAGE_WRITER.build_package_bytes(plan)


def keyed_sample(name: str) -> ExamNetQtiSamplePackage:
    samples = {sample.name: sample for sample in examnet_qti_keyed_samples()}
    return samples[name]


def write_sample(sample: ExamNetQtiSamplePackage, root: Path) -> Path:
    sample_dir = root / str(sample.name)
    sample_dir.mkdir(parents=True, exist_ok=True)
    plan = build_examnet_qti_package_plan(
        package_name=sample.name, assessment_title=sample.name, items=sample.items
    )
    package_bytes: bytes | None = None
    if plan.status == ExamNetQtiPackageStatus.PASSED:
        package_bytes = QTI_PACKAGE_WRITER.build_package_bytes(plan)
        (sample_dir / sample.package_filename).write_bytes(package_bytes)
    report_bytes = QTI_PACKAGE_WRITER.build_validation_report_bytes(
        plan=plan,
        package_filename=sample.package_filename,
        package_bytes=package_bytes,
    )
    (sample_dir / sample.report_filename).write_bytes(report_bytes)
    return sample_dir


def read_report(path: Path) -> dict[str, object]:
    data: object = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return {str(key): value for key, value in data.items()}


def json_string(data: dict[str, object], key: str) -> str:
    value = data[key]
    assert isinstance(value, str)
    return value


def first_manual_follow_up(report: dict[str, object]) -> dict[str, object]:
    value = report["manual_follow_ups"]
    assert isinstance(value, list)
    first = value[0]
    assert isinstance(first, dict)
    return {str(key): child for key, child in first.items()}


def item_body_paragraphs(item: ElementTree.Element) -> list[ElementTree.Element]:
    return item.findall(f"{{{QTI_NAMESPACE}}}qti-item-body/{{{QTI_NAMESPACE}}}p")
