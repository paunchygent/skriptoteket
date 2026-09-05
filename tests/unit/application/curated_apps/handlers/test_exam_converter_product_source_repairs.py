"""Stored product regressions for deterministic DigiExam source repairs."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubJobStatus,
    ConversionHubOutputFormatV2,
    ConversionHubSourceFormatV2,
)
from skriptoteket.application.curated_apps.exam_conversion_producers import (
    InProcessExamConversionProducer,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import ConversionHubUpload
from skriptoteket.application.curated_apps.handlers.exam_converter_product import (
    ExamConverterProductHandler,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamWarningCode,
)
from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_conversion_artifacts import (
    FilesystemExamConversionArtifactStore,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_pdf_renderer import (
    WeasyPrintExamNetPdfRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from tests.unit.application.curated_apps.handlers.test_exam_converter_product import (
    FakeUow,
    JobRepository,
    ProposalRepository,
    SessionRepository,
)

pytestmark = pytest.mark.unit


def _upload(*, repair: bool) -> ConversionHubUpload:
    if repair:
        questions: list[dict[str, object]] = [
            {
                "id": 1,
                "title": "  ",
                "about": "Titta på bilden.",
                "bodyHTML": (
                    '<p>Titta på bilden.</p><p><img data-image-id="0" class="fr-fic" /></p>'
                ),
                "images": [],
                "maxScore": 10.5,
                "type": 0,
            }
        ]
        filename = "repair.dxe"
    else:
        questions = [
            {
                "id": 1,
                "title": "Fritext med decimalpoäng",
                "about": "",
                "bodyHTML": "<p>Svara fritt.</p>",
                "images": [],
                "maxScore": 10.5,
                "type": 0,
            },
            {
                "id": 2,
                "title": "Fritext med liten decimalpoäng",
                "about": "",
                "bodyHTML": "<p>Svara fritt.</p>",
                "images": [],
                "maxScore": 0.25,
                "type": 0,
            },
        ]
        filename = "fractional.dxe"
    return ConversionHubUpload(
        filename=filename,
        content_type="application/octet-stream",
        file_bytes=json.dumps({"exams": [{"questions": questions}]}).encode(),
    )


async def _stored_product(
    tmp_path: Path, *, repair: bool
) -> tuple[
    User, ConversionHubJob, FilesystemExamConversionArtifactStore, ExamConverterProductHandler
]:
    now = datetime(2026, 9, 4, tzinfo=UTC)
    actor = User(
        id=uuid4(),
        email="teacher@example.test",
        role=Role.USER,
        auth_provider=AuthProvider.HULEEDU,
        created_at=now,
        updated_at=now,
    )
    job = ConversionHubJob(
        id=uuid4(),
        owner_user_id=actor.id,
        input_filename="exam.dxe",
        source_format=ConversionHubSourceFormatV2.DIGIEXAM_DXE,
        output_format=ConversionHubOutputFormatV2.EXAMNET_BUNDLE,
        upstream_job_id=None,
        status=ConversionHubJobStatus.SUCCEEDED,
        created_at=now,
        updated_at=now,
    )
    producer = InProcessExamConversionProducer(
        qti_writer=ExamNetQtiPackageWriter(),
        pdf_renderer=WeasyPrintExamNetPdfRenderer(),
    )
    artifacts = FilesystemExamConversionArtifactStore(artifacts_root=tmp_path)
    handler = ExamConverterProductHandler(
        jobs=JobRepository(job),
        sessions=SessionRepository(),
        proposals=ProposalRepository(),
        producer=producer,
        artifacts=artifacts,
        uow=FakeUow(),
    )
    artifacts.store_artifact(
        job_id=job.id,
        artifact=await producer.convert(
            job_id=job.id,
            upload=_upload(repair=repair),
            overlay_bytes=None,
            correlation_id=None,
        ),
    )
    return actor, job, artifacts, handler


@pytest.mark.asyncio
async def test_stored_product_preserves_fractional_scores_and_fingerprints(
    tmp_path: Path,
) -> None:
    actor, job, artifacts, handler = await _stored_product(tmp_path, repair=False)

    result = await handler.result(actor=actor, job_id=job.id)
    ir_json = artifacts.read_named_artifact(job_id=job.id, artifact_key="ir_json")
    source_ir_json = artifacts.read_named_artifact(job_id=job.id, artifact_key="source_ir_json")
    manifest = json.loads(
        artifacts.read_named_artifact(
            job_id=job.id,
            artifact_key="migration_manifest",
        ).content
    )

    assert result.warning_count == 0
    assert [item["max_score"] for item in json.loads(ir_json.content)["items"]] == [10.5, 0.25]
    assert [item["max_score"] for item in json.loads(source_ir_json.content)["items"]] == [
        10.5,
        0.25,
    ]
    fingerprints = [item["source_item_fingerprint"] for item in manifest["item_summaries"]]
    assert all(fingerprint.startswith("sha256:") for fingerprint in fingerprints)
    assert fingerprints[0] != fingerprints[1]
    assert manifest["warning_count"] == 0


@pytest.mark.asyncio
async def test_stored_product_keeps_item_bound_repair_warnings_and_real_count(
    tmp_path: Path,
) -> None:
    actor, job, artifacts, handler = await _stored_product(tmp_path, repair=True)

    result = await handler.result(actor=actor, job_id=job.id)
    manifest = json.loads(
        artifacts.read_named_artifact(
            job_id=job.id,
            artifact_key="migration_manifest",
        ).content
    )
    payload = json.loads(
        artifacts.read_named_artifact(job_id=job.id, artifact_key="ir_json").content
    )
    by_code = {warning["code"]: warning for warning in payload["items"][0]["warnings"]}

    assert manifest["warning_count"] == 2
    assert result.warning_count == manifest["warning_count"]
    assert result.manual_follow_up_required is False
    assert payload["items"][0]["max_score"] == 10.5
    assert set(by_code) == {
        DigiExamWarningCode.MISSING_QUESTION_TITLE,
        DigiExamWarningCode.MISSING_PROMPT_IMAGE,
    }
    assert all(warning["blocking"] is False for warning in by_code.values())
    assert by_code[DigiExamWarningCode.MISSING_QUESTION_TITLE]["message"] == (
        "Fråga 1 saknade titel. "
        "Titeln ”Question 1” lades till automatiskt. "
        "Kontrollera titeln innan du använder provet."
    )
    assert by_code[DigiExamWarningCode.MISSING_PROMPT_IMAGE]["message"] == (
        "Bilden i fråga 1 saknas. Lägg till den innan du använder provet."
    )
