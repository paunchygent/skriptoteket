from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from skriptoteket.application.curated_apps.exam_conversion_producers import (
    InProcessExamConversionProducer,
)
from skriptoteket.application.curated_apps.public_exam_converter import (
    PublicExamConverterJobStatus,
    PublicExamConverterSubmittedJob,
    PublicExamConverterTarget,
    PublicExamConverterUpload,
)
from skriptoteket.application.curated_apps.public_exam_converter_local_execution import (
    PublicExamConverterLocalExecutor,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    public_exam_converter_store,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_pdf_renderer import (
    WeasyPrintExamNetPdfRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from skriptoteket.protocols.documents import PdfTextExtractionProbe

_FIXTURE = (
    Path(__file__).parents[3]
    / "fixtures"
    / "exam_conversion"
    / "1772718003-test-samma-prov-i-digiexam.dxe"
)
_NOW = datetime(2026, 8, 30, 8, 0, tzinfo=UTC)
_JOB_ID = UUID("4f27d43f-7c2e-4c9c-a4df-2d799f88527a")


class FixedClock:
    def now(self) -> datetime:
        return _NOW


class UnusedPdfTextExtractor:
    def probe_text(self, *, file_bytes: bytes, filename: str) -> PdfTextExtractionProbe:
        del file_bytes, filename
        return PdfTextExtractionProbe(text=None)

    def extract_text(self, *, file_bytes: bytes, filename: str) -> str | None:
        del file_bytes, filename
        raise AssertionError("No graded-result PDF was supplied")


class FixedPdfTextExtractor:
    def extract_text(self, *, file_bytes: bytes, filename: str) -> str | None:
        assert file_bytes == b"%PDF graded result"
        assert filename == "graded-result.pdf"
        return "\n".join(
            (
                "Elevresultat",
                "Flervalsfråga typ 1",
                "(Korrekt svar) Första alternativet",
                "Elevresultat",
                "Ytterligare en flervalsfråga",
                "(Korrekt svar) Andra alternativet",
            )
        )

    def probe_text(self, *, file_bytes: bytes, filename: str) -> PdfTextExtractionProbe:
        text = self.extract_text(file_bytes=file_bytes, filename=filename)
        return PdfTextExtractionProbe(text=text)


@pytest.mark.asyncio
async def test_local_executor_completes_real_dxe_without_remote_provider() -> None:
    store = public_exam_converter_store.InMemoryPublicExamConverterJobStore()
    executor = PublicExamConverterLocalExecutor(
        store=store,
        producer=InProcessExamConversionProducer(
            qti_writer=ExamNetQtiPackageWriter(),
            pdf_renderer=WeasyPrintExamNetPdfRenderer(),
        ),
        pdf_text_extractor=UnusedPdfTextExtractor(),
        clock=FixedClock(),
    )
    job = PublicExamConverterSubmittedJob(
        public_job_id=str(_JOB_ID),
        local_job_id=_JOB_ID,
        requested_targets=(
            PublicExamConverterTarget.EXAMNET_PDF,
            PublicExamConverterTarget.QTI_PACKAGE,
        ),
        status=PublicExamConverterJobStatus.QUEUED,
        source_filename=_FIXTURE.name,
        submitted_at=_NOW,
        updated_at=_NOW,
        expires_at=_NOW + timedelta(hours=1),
        correlation_id="public-local-test",
    )
    await store.create(job=job)

    await executor.enqueue(
        job=job,
        source_dxe=PublicExamConverterUpload(
            filename=_FIXTURE.name,
            content_type="application/octet-stream",
            file_bytes=_FIXTURE.read_bytes(),
        ),
        graded_result_pdf=None,
        correlation_id="public-local-test",
    )

    completed = await _wait_for_terminal(store=store)
    assert completed.status is PublicExamConverterJobStatus.SUCCEEDED
    assert completed.artifact is not None
    assert completed.result == {
        "conversion_metadata": {"route_key": "digiexam_dxe_to_examnet_migration_bundle"},
        "source": {"filename": _FIXTURE.name, "format": "digiexam_dxe"},
        "requested_targets": ["examnet_pdf", "qti_package"],
    }
    assert {artifact.artifact_key for artifact in completed.artifact.named_artifacts} >= {
        "examnet_pdf",
        "qti_package",
        "qti_validation_report",
        "target_readiness_report",
    }


@pytest.mark.asyncio
async def test_local_executor_applies_optional_graded_result_pdf_evidence() -> None:
    store = public_exam_converter_store.InMemoryPublicExamConverterJobStore()
    executor = PublicExamConverterLocalExecutor(
        store=store,
        producer=InProcessExamConversionProducer(
            qti_writer=ExamNetQtiPackageWriter(),
            pdf_renderer=WeasyPrintExamNetPdfRenderer(),
        ),
        pdf_text_extractor=FixedPdfTextExtractor(),
        clock=FixedClock(),
    )
    job = PublicExamConverterSubmittedJob(
        public_job_id=str(_JOB_ID),
        local_job_id=_JOB_ID,
        requested_targets=(PublicExamConverterTarget.EXAMNET_PDF,),
        status=PublicExamConverterJobStatus.QUEUED,
        source_filename=_FIXTURE.name,
        submitted_at=_NOW,
        updated_at=_NOW,
        expires_at=_NOW + timedelta(hours=1),
        correlation_id="public-graded-result-test",
    )
    await store.create(job=job)

    await executor.enqueue(
        job=job,
        source_dxe=PublicExamConverterUpload(
            filename=_FIXTURE.name,
            content_type="application/octet-stream",
            file_bytes=_FIXTURE.read_bytes(),
        ),
        graded_result_pdf=PublicExamConverterUpload(
            filename="graded-result.pdf",
            content_type="application/pdf",
            file_bytes=b"%PDF graded result",
        ),
        correlation_id="public-graded-result-test",
    )

    completed = await _wait_for_terminal(store=store)
    assert completed.status is PublicExamConverterJobStatus.SUCCEEDED
    assert completed.artifact is not None
    source_ir = next(
        artifact
        for artifact in completed.artifact.named_artifacts
        if artifact.artifact_key == "source_ir_json"
    )
    source_ir_payload = json.loads(source_ir.content)
    assert isinstance(source_ir_payload, dict)
    items = source_ir_payload["items"]
    assert isinstance(items, list)
    graded_item = next(
        item
        for item in items
        if isinstance(item, dict) and item.get("title") == "Flervalsfråga typ 1"
    )
    answer_key = graded_item["answer_key"]
    assert isinstance(answer_key, dict)
    assert answer_key["provenance"] == "graded_result_pdf_correct_labels"


async def _wait_for_terminal(
    *,
    store: public_exam_converter_store.InMemoryPublicExamConverterJobStore,
) -> PublicExamConverterSubmittedJob:
    for _attempt in range(100):
        job = await store.get(public_job_id=str(_JOB_ID), now=_NOW)
        if job is not None and job.status in {
            PublicExamConverterJobStatus.SUCCEEDED,
            PublicExamConverterJobStatus.FAILED,
        }:
            return job
        await asyncio.sleep(0)
    raise AssertionError("Local public conversion did not reach a terminal state")
