"""Exam workspace export builders for the Exam.net QTI lane.

Purpose:
    Build fail-closed Exam.net QTI package and validation-report bytes from a
    native exam document: export gate, plan gate, and report gate all raise
    `DomainError` instead of handing out unproven artifacts.

Relationships:
    - Consumes the native adapter in
      `domain.curated_apps.exam_workspace.examnet_qti_export` and the planner
      in `domain.curated_apps.exam_conversion.examnet_qti_package`.
    - Receives the deterministic writer through
      `protocols.exam_conversion.ExamNetQtiPackageWriterProtocol`, mirroring
      `application.curated_apps.exam_conversion_producers`.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiPackageStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_package import (
    build_examnet_qti_package_plan,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    NO_EXPORT_ASSETS,
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    native_export_blockers,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.exam_conversion import ExamNetQtiPackageWriterProtocol


def build_native_examnet_qti_package(
    document: NativeExamDocument,
    *,
    package_name: str,
    qti_writer: ExamNetQtiPackageWriterProtocol,
    assets_by_id: Mapping[str, bytes] = NO_EXPORT_ASSETS,
) -> tuple[bytes, bytes]:
    """Return (package_bytes, validation_report_bytes) or fail closed."""

    blockers = native_export_blockers(document)
    if blockers:
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="The exam document is not ready for QTI export.",
            details={
                "blockers": [blocker.model_dump(mode="json") for blocker in blockers],
            },
        )

    items = native_exam_to_examnet_qti_items(document, assets_by_id=assets_by_id)
    plan = build_examnet_qti_package_plan(package_name=package_name, items=items)
    if plan.status is not ExamNetQtiPackageStatus.PASSED:
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="The QTI package plan did not pass planning checks.",
            details={"plan_status": plan.status.value, "warnings": list(plan.warnings)},
        )

    package_bytes = qti_writer.build_package_bytes(plan)
    report_bytes = qti_writer.build_validation_report_bytes(
        plan=plan,
        package_filename=f"{package_name}.zip",
        package_bytes=package_bytes,
    )
    _raise_unless_report_passed(report_bytes)
    return package_bytes, report_bytes


def _raise_unless_report_passed(report_bytes: bytes) -> None:
    try:
        report = json.loads(report_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="The QTI validation report is not valid JSON.",
        ) from error
    package_status = report.get("package_status") if isinstance(report, dict) else None
    if package_status != ExamNetQtiPackageStatus.PASSED.value:
        errors = report.get("errors", []) if isinstance(report, dict) else []
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="The generated QTI package failed validation.",
            details={"package_status": package_status, "errors": errors},
        )
