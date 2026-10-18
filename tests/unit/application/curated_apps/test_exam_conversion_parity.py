"""Parity proof for the in-process dxe -> Exam.net bundle walking skeleton.

Purpose:
    Prove that the exam-conversion chain reproduces the committed reference
    outputs for one real DigiExam fixture whose answer keys come from
    deterministic graded-result evidence: byte parity with the QTI 3.0 package
    regenerated in TASK-SKRIPT-39-09-01 and deterministic structural parity
    for the Exam.net-profile PDF. Also pin the public converter's named review
    artifacts and its manual-follow-up and blocked outcomes.

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
from uuid import UUID

import pytest
from pypdf import PdfReader

from skriptoteket.application.curated_apps.exam_conversion import (
    EXAMNET_BUNDLE_PDF_FILENAME,
    EXAMNET_BUNDLE_QTI_PACKAGE_FILENAME,
    EXAMNET_BUNDLE_QTI_VALIDATION_REPORT_FILENAME,
    ExamConversionStoredArtifact,
)
from skriptoteket.application.curated_apps.exam_conversion_producers import (
    InProcessExamConversionProducer,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import (
    ConversionHubUpload,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_dxe_parser import (
    DigiExamDxeParser,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_result_pdf_answers import (
    DigiExamResultPdfAnswerEvidence,
    DigiExamResultPdfAnswerItem,
)
from skriptoteket.domain.errors import DomainError
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_pdf_renderer import (
    WeasyPrintExamNetPdfRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)

_FIXTURE_DIR = Path("tests/fixtures/exam_conversion")
_DXE_FILENAME = "1772718003-test-samma-prov-i-digiexam.dxe"


def _upload() -> ConversionHubUpload:
    return ConversionHubUpload(
        filename=_DXE_FILENAME,
        content_type="application/octet-stream",
        file_bytes=(_FIXTURE_DIR / _DXE_FILENAME).read_bytes(),
    )


def _producer() -> InProcessExamConversionProducer:
    return InProcessExamConversionProducer(
        qti_writer=ExamNetQtiPackageWriter(),
        pdf_renderer=WeasyPrintExamNetPdfRenderer(),
    )


def _answer_evidence() -> DigiExamResultPdfAnswerEvidence:
    """Key every choice item with alternative 1 and the gap item with "svar" per gap."""

    parsed = DigiExamDxeParser().parse_text(
        _upload().file_bytes.decode("utf-8"), filename=_DXE_FILENAME
    )
    items: list[DigiExamResultPdfAnswerItem] = []
    for item in parsed.items:
        if item.alternatives:
            items.append(
                DigiExamResultPdfAnswerItem(
                    title=item.header,
                    correct_alternative_texts=tuple(
                        alternative.title
                        for alternative in item.alternatives
                        if alternative.id == 1
                    ),
                    correct_gap_values=(),
                )
            )
        elif item.gaps:
            items.append(
                DigiExamResultPdfAnswerItem(
                    title=item.header,
                    correct_alternative_texts=(),
                    correct_gap_values=("svar",) * len(item.gaps),
                )
            )
    return DigiExamResultPdfAnswerEvidence(items=tuple(items))


@pytest.fixture(scope="module")
async def keyed_artifact() -> ExamConversionStoredArtifact:
    artifact = await _producer().convert(
        job_id=UUID(int=0),
        upload=_upload(),
        answer_evidence=_answer_evidence(),
        enrichment_failure_code=None,
        correlation_id=None,
    )
    assert artifact.filename == "1772718003-test-samma-prov-i-digiexam-examnet-bundle.zip"
    assert artifact.content_type == "application/zip"
    return artifact


@pytest.fixture(scope="module")
async def bundle_entries(keyed_artifact: ExamConversionStoredArtifact) -> dict[str, bytes]:
    with zipfile.ZipFile(BytesIO(keyed_artifact.content)) as bundle:
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
def test_qti_package_bytes_match_the_committed_reference(
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
        # PDF font encoding varies by host for NBSP; preserve every other character and newline.
        assert produced_page.extract_text().replace(
            "\u00a0", " "
        ) == reference_page.extract_text().replace("\u00a0", " ")


@pytest.mark.unit
def test_keyed_conversion_publishes_the_public_review_artifacts(
    keyed_artifact: ExamConversionStoredArtifact,
) -> None:
    artifacts = {named.artifact_key: named for named in keyed_artifact.named_artifacts}

    assert list(artifacts) == [
        "examnet_pdf",
        "qti_package",
        "qti_validation_report",
        "ir_json",
        "source_ir_json",
        "migration_manifest",
        "target_readiness_report",
        "answer_key_review_state_report",
        "answer_key_completion_report",
    ]
    assert artifacts["ir_json"].content == artifacts["source_ir_json"].content
    readiness = json.loads(artifacts["target_readiness_report"].content)
    assert [row["item_id"] for row in readiness["targets"]] == [None, None]
    assert all(row["export_enabled"] is True for row in readiness["targets"])
    review_state = json.loads(artifacts["answer_key_review_state_report"].content)
    origins = {row["item_id"]: row["current_key_origin"] for row in review_state["items"]}
    assert sorted(origins) == [f"item-00{n}" for n in range(1, 8)]
    assert set(origins.values()) == {"source_provided"}
    assert all(row["provenance_detail"] is None for row in review_state["items"])
    completion = json.loads(artifacts["answer_key_completion_report"].content)
    assert {row["decision_state"] for row in completion["items"]} == {"skipped"}
    assert {row["backend_status"] for row in completion["items"]} == {"not_requested"}
    assert all(row["answer_payload"] is None for row in completion["items"])


@pytest.mark.unit
async def test_unkeyed_conversion_with_failure_code_emits_the_manual_follow_up_bundle() -> None:
    artifact = await _producer().convert(
        job_id=UUID(int=1),
        upload=_upload(),
        answer_evidence=None,
        enrichment_failure_code="manual_follow_up_test_code",
        correlation_id=None,
    )

    with zipfile.ZipFile(BytesIO(artifact.content)) as bundle:
        inner = bundle.read(EXAMNET_BUNDLE_QTI_PACKAGE_FILENAME)
        validation_report = json.loads(bundle.read(EXAMNET_BUNDLE_QTI_VALIDATION_REPORT_FILENAME))
    with zipfile.ZipFile(BytesIO(inner)) as package:
        assert package.namelist() == ["manual-follow-up.json"]
    assert validation_report == {
        "failure_code": "manual_follow_up_test_code",
        "schema_version": "qti_validation_report_v1",
        "status": "manual_follow_up_required",
    }
    artifacts = {named.artifact_key: named for named in artifact.named_artifacts}
    readiness = json.loads(artifacts["target_readiness_report"].content)
    blocked_items = {row["item_id"] for row in readiness["targets"] if row["item_id"]}
    assert blocked_items == {f"item-00{n}" for n in range(2, 8)}
    assert all(row["export_enabled"] is False for row in readiness["targets"])
    completion = json.loads(artifacts["answer_key_completion_report"].content)
    by_item = {row["item_id"]: row for row in completion["items"]}
    assert by_item["item-001"]["backend_status"] == "not_requested"
    for item_id in blocked_items:
        assert by_item[item_id]["backend_status"] == "failed"
        assert by_item[item_id]["backend_failure_code"] == "manual_follow_up_test_code"
        assert by_item[item_id]["decision_state"] == "manual_follow_up_required"


@pytest.mark.unit
async def test_unkeyed_conversion_without_failure_code_is_rejected() -> None:
    with pytest.raises(DomainError):
        await _producer().convert(
            job_id=UUID(int=2),
            upload=_upload(),
            answer_evidence=None,
            enrichment_failure_code=None,
            correlation_id=None,
        )
