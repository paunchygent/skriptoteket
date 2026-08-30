"""API tests for the in-process Exam Converter conversion lane.

Purpose:
    Prove the authenticated dxe -> Exam.net bundle flow end to end through the
    Conversion Hub API surface: submit one `.dxe`, read job status, and
    download the bundle through the existing artifact download route, without
    ever touching the Sir Convert client.

Relationships:
    - Uses the signed HuleEdu Gateway-equivalent local auth harness from
      ``tests.fixtures.profile_app_continuation_support``.
    - Exercises ``CreateExamConverterConversionJobsHandler`` with the real
      producer, QTI writer, WeasyPrint renderer, and filesystem artifact store.
"""

from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path

import httpx
import pytest

from skriptoteket.application.curated_apps.exam_conversion import ExamConverterConversionLane
from tests.unit.web.exam_converter.conftest import InMemoryConversionHubJobRepository

pytestmark = pytest.mark.unit

_FIXTURE_DIR = Path("tests/fixtures/exam_conversion")
_DXE_FILENAME = "1772718003-test-samma-prov-i-digiexam.dxe"
_BASE = "/api/v1/apps/documents.conversion_hub"


async def test_in_process_lane_converts_and_serves_bundle_through_job_surface(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    jobs_repository: InMemoryConversionHubJobRepository,
) -> None:
    submit_response = await client.post(
        f"{_BASE}/exam-converter/conversions",
        headers=auth_headers,
        data={"idempotency_key": "test-keyed-conversion"},
        files={
            "file": (
                _DXE_FILENAME,
                (_FIXTURE_DIR / _DXE_FILENAME).read_bytes(),
                "application/octet-stream",
            ),
            "ingestion_overlay": (
                "teacher-overlay.json",
                (_FIXTURE_DIR / "teacher-overlay.json").read_bytes(),
                "application/json",
            ),
        },
    )

    assert submit_response.status_code == 200
    submitted = submit_response.json()
    assert submitted["status"] == "succeeded"
    assert submitted["error"] is None
    job_id = submitted["job_id"]
    stored_job = jobs_repository.jobs[next(iter(jobs_repository.jobs))]
    assert stored_job.upstream_job_id == f"local-exam:{job_id}"

    status_response = await client.get(f"{_BASE}/jobs/{job_id}", headers=auth_headers)
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "succeeded"

    artifact_response = await client.get(f"{_BASE}/jobs/{job_id}/artifact", headers=auth_headers)
    assert artifact_response.status_code == 200
    assert artifact_response.headers["content-type"].startswith("application/zip")
    assert "examnet-bundle.zip" in artifact_response.headers["content-disposition"]

    with zipfile.ZipFile(BytesIO(artifact_response.content)) as bundle:
        names = set(bundle.namelist())
        assert names == {"qti-package.zip", "examnet-import.pdf", "qti-validation-report.json"}
        qti_bytes = bundle.read("qti-package.zip")
    assert qti_bytes == (_FIXTURE_DIR / "reference-qti-package.zip").read_bytes()


async def test_in_process_lane_fails_job_when_answer_keys_are_missing(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    submit_response = await client.post(
        f"{_BASE}/exam-converter/conversions",
        headers=auth_headers,
        data={"idempotency_key": "test-unkeyed-conversion"},
        files={
            "file": (
                _DXE_FILENAME,
                (_FIXTURE_DIR / _DXE_FILENAME).read_bytes(),
                "application/octet-stream",
            ),
        },
    )

    assert submit_response.status_code == 200
    submitted = submit_response.json()
    assert submitted["status"] == "failed"
    assert submitted["error"] is not None
    assert "facit" in submitted["error"]


async def test_conversion_route_rejects_non_dxe_uploads(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client.post(
        f"{_BASE}/exam-converter/conversions",
        headers=auth_headers,
        data={"idempotency_key": "test-invalid-upload"},
        files={"file": ("notes.pdf", b"%PDF-1.7", "application/pdf")},
    )

    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_conversion_route_requires_authentication(client: httpx.AsyncClient) -> None:
    response = await client.post(
        f"{_BASE}/exam-converter/conversions",
        files={"file": (_DXE_FILENAME, b"{}", "application/octet-stream")},
    )

    assert response.status_code == 401


class TestSirConvertLaneDefault:
    @pytest.fixture
    def lane(self) -> ExamConverterConversionLane:
        return ExamConverterConversionLane(value="sir_convert")

    async def test_conversion_route_is_disabled_on_the_sir_convert_lane(
        self,
        client: httpx.AsyncClient,
        auth_headers: dict[str, str],
        jobs_repository: InMemoryConversionHubJobRepository,
    ) -> None:
        response = await client.post(
            f"{_BASE}/exam-converter/conversions",
            headers=auth_headers,
            data={"idempotency_key": "test-disabled-lane"},
            files={
                "file": (
                    _DXE_FILENAME,
                    (_FIXTURE_DIR / _DXE_FILENAME).read_bytes(),
                    "application/octet-stream",
                ),
            },
        )

        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
        assert "inte aktiverad" in response.json()["error"]["message"]
        assert jobs_repository.jobs == {}
