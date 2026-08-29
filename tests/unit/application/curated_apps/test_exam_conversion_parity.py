"""Parity proof for the in-process dxe -> Exam.net bundle walking skeleton.

Purpose:
    Prove that the ported exam-conversion chain reproduces the Sir
    Convert-a-Lot outputs at revision 41be61a6 for one real DigiExam fixture
    with a deterministic teacher overlay: byte parity for the QTI package and
    deterministic structural parity for the Exam.net-profile PDF.

Relationships:
    Exercises ``InProcessExamConversionProducer`` with the real QTI package
    writer and WeasyPrint renderer against the committed reference artifacts
    under ``tests/fixtures/exam_conversion/``.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfReader

from skriptoteket.application.curated_apps.exam_conversion import (
    EXAMNET_BUNDLE_PDF_FILENAME,
    EXAMNET_BUNDLE_QTI_PACKAGE_FILENAME,
    EXAMNET_BUNDLE_QTI_VALIDATION_REPORT_FILENAME,
)
from skriptoteket.application.curated_apps.exam_conversion_producers import (
    InProcessExamConversionProducer,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import (
    ConversionHubUpload,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_pdf_renderer import (
    WeasyPrintExamNetPdfRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)

_FIXTURE_DIR = Path("tests/fixtures/exam_conversion")
_DXE_FILENAME = "1772718003-test-samma-prov-i-digiexam.dxe"


@pytest.fixture(scope="module")
async def bundle_entries() -> dict[str, bytes]:
    producer = InProcessExamConversionProducer(
        qti_writer=ExamNetQtiPackageWriter(),
        pdf_renderer=WeasyPrintExamNetPdfRenderer(),
    )
    upload = ConversionHubUpload(
        filename=_DXE_FILENAME,
        content_type="application/octet-stream",
        file_bytes=(_FIXTURE_DIR / _DXE_FILENAME).read_bytes(),
    )
    artifact = await producer.convert(
        upload=upload,
        overlay_bytes=(_FIXTURE_DIR / "teacher-overlay.json").read_bytes(),
        correlation_id=None,
    )
    assert artifact.filename == "1772718003-test-samma-prov-i-digiexam-examnet-bundle.zip"
    assert artifact.content_type == "application/zip"
    with zipfile.ZipFile(BytesIO(artifact.content)) as bundle:
        return {name: bundle.read(name) for name in bundle.namelist()}


@pytest.mark.unit
def test_bundle_contains_the_three_examnet_artifacts(bundle_entries: dict[str, bytes]) -> None:
    assert sorted(bundle_entries) == sorted(
        (
            EXAMNET_BUNDLE_QTI_PACKAGE_FILENAME,
            EXAMNET_BUNDLE_PDF_FILENAME,
            EXAMNET_BUNDLE_QTI_VALIDATION_REPORT_FILENAME,
        )
    )


@pytest.mark.unit
def test_qti_package_bytes_match_sir_convert_reference(
    bundle_entries: dict[str, bytes],
) -> None:
    reference = (_FIXTURE_DIR / "reference-qti-package.zip").read_bytes()
    produced = bundle_entries[EXAMNET_BUNDLE_QTI_PACKAGE_FILENAME]

    assert hashlib.sha256(produced).hexdigest() == hashlib.sha256(reference).hexdigest()
    assert produced == reference


@pytest.mark.unit
def test_qti_package_hash_matches_recorded_reference_summary(
    bundle_entries: dict[str, bytes],
) -> None:
    summary = json.loads((_FIXTURE_DIR / "reference-summary.json").read_text(encoding="utf-8"))
    produced = bundle_entries[EXAMNET_BUNDLE_QTI_PACKAGE_FILENAME]

    assert f"sha256:{hashlib.sha256(produced).hexdigest()}" == summary["qti_package_sha256"]


@pytest.mark.unit
def test_qti_validation_report_is_passed_and_binds_the_package(
    bundle_entries: dict[str, bytes],
) -> None:
    report = json.loads(bundle_entries[EXAMNET_BUNDLE_QTI_VALIDATION_REPORT_FILENAME])
    produced = bundle_entries[EXAMNET_BUNDLE_QTI_PACKAGE_FILENAME]

    assert report["package_status"] == "passed"
    assert report["package_sha256"] == hashlib.sha256(produced).hexdigest()


@pytest.mark.unit
def test_examnet_pdf_matches_sir_convert_reference_structurally(
    bundle_entries: dict[str, bytes],
) -> None:
    produced = PdfReader(BytesIO(bundle_entries[EXAMNET_BUNDLE_PDF_FILENAME]))
    reference = PdfReader(BytesIO((_FIXTURE_DIR / "reference-examnet-import.pdf").read_bytes()))

    assert len(produced.pages) == len(reference.pages)
    for produced_page, reference_page in zip(produced.pages, reference.pages, strict=True):
        assert produced_page.extract_text() == reference_page.extract_text()
