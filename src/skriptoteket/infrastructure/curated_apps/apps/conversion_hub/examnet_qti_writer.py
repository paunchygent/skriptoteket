"""Deterministic materialization for Exam.net-oriented QTI packages.

Purpose:
    Build deterministic QTI zip package bytes, validation-report bytes, and
    bundle zip bytes from the filesystem-free exam-conversion domain plans.

Relationships:
    Implements ``ExamNetQtiPackageWriterProtocol`` for the in-process Exam
    Converter producer. Ports the Sir Convert-a-Lot package writer at revision
    41be61a6 without its filesystem artifact orchestration.
"""

from __future__ import annotations

import json
import zipfile
from io import BytesIO

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiPackagePlan,
    ExamNetQtiPackageStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_validation import (
    build_examnet_qti_validation_report,
    examnet_qti_validation_report_to_json_data,
)
from skriptoteket.protocols.exam_conversion import ExamNetQtiPackageWriterProtocol

_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


class ExamNetQtiPackageWriter(ExamNetQtiPackageWriterProtocol):
    """Write deterministic QTI package, report, and bundle bytes."""

    def build_package_bytes(self, plan: ExamNetQtiPackagePlan) -> bytes:
        """Return deterministic zip bytes for a passed QTI package plan."""
        if plan.status != ExamNetQtiPackageStatus.PASSED:
            raise ValueError("Only passed QTI package plans can be materialized as zip bytes.")
        return _deterministic_zip_bytes(
            entries=tuple((file.relative_path, file.payload) for file in plan.files)
        )

    def build_validation_report_bytes(
        self,
        *,
        plan: ExamNetQtiPackagePlan,
        package_filename: str,
        package_bytes: bytes | None,
    ) -> bytes:
        """Return deterministic JSON bytes for the QTI validation report."""
        report = build_examnet_qti_validation_report(
            plan=plan,
            package_filename=package_filename,
            package_bytes=package_bytes,
        )
        report_data = examnet_qti_validation_report_to_json_data(report)
        text = json.dumps(report_data, ensure_ascii=False, indent=2, sort_keys=True)
        return f"{text}\n".encode("utf-8")

    def build_bundle_bytes(self, *, entries: tuple[tuple[str, bytes], ...]) -> bytes:
        """Return deterministic zip bytes for the downloadable bundle."""
        return _deterministic_zip_bytes(entries=entries)


def _deterministic_zip_bytes(*, entries: tuple[tuple[str, bytes], ...]) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative_path, payload in entries:
            info = zipfile.ZipInfo(relative_path, date_time=_ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, payload)
    return buffer.getvalue()
