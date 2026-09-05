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

import json
import zipfile
from io import BytesIO
from pathlib import Path

import httpx
import pytest

from tests.unit.web.exam_converter.conftest import InMemoryConversionHubJobRepository

pytestmark = pytest.mark.unit

_FIXTURE_DIR = Path("tests/fixtures/exam_conversion")
_DXE_FIXTURE_FILENAME = "1772718003-test-samma-prov-i-digiexam.dxe"
_BASE = "/api/v1/apps/documents.conversion_hub"


async def test_local_conversion_converts_and_serves_bundle_through_job_surface(
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
                _DXE_FIXTURE_FILENAME,
                (_FIXTURE_DIR / _DXE_FIXTURE_FILENAME).read_bytes(),
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
    assert stored_job.upstream_job_id is None

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
        validation_report = json.loads(bundle.read("qti-validation-report.json"))
    assert qti_bytes == (_FIXTURE_DIR / "reference-qti-package.zip").read_bytes()
    assert validation_report["package_filename"] == "qti-package.zip"

    manifest_response = await client.get(
        f"{_BASE}/exam-converter/jobs/{job_id}/artifacts",
        headers=auth_headers,
    )
    assert manifest_response.status_code == 200
    manifest_by_key = {
        entry["artifact_key"]: entry for entry in manifest_response.json()["artifacts"]
    }
    assert manifest_by_key["examnet_pdf"]["filename"] == (
        "1772718003-test-samma-prov-i-digiexam - Exam.net.pdf"
    )
    assert manifest_by_key["qti_package"]["filename"] == (
        "1772718003-test-samma-prov-i-digiexam - QTI.zip"
    )

    pdf_response = await client.get(
        f"{_BASE}/exam-converter/jobs/{job_id}/artifacts/examnet_pdf",
        headers=auth_headers,
    )
    qti_response = await client.get(
        f"{_BASE}/exam-converter/jobs/{job_id}/artifacts/qti_package",
        headers=auth_headers,
    )
    assert pdf_response.headers["content-disposition"] == (
        'attachment; filename="1772718003-test-samma-prov-i-digiexam - Exam.net.pdf"'
    )
    assert qti_response.headers["content-disposition"] == (
        'attachment; filename="1772718003-test-samma-prov-i-digiexam - QTI.zip"'
    )
    assert qti_response.content == qti_bytes


async def test_quoted_source_filename_uses_extended_content_disposition(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    keyed_payload = json.dumps(
        {
            "exams": [
                {
                    "questions": [
                        {
                            "id": 1,
                            "title": "Single choice",
                            "about": "",
                            "bodyHTML": "<p>Choose.</p>",
                            "images": [],
                            "maxScore": 2,
                            "type": 1,
                            "alternatives": [
                                {"id": 1, "title": "Alpha", "about": "", "right": False},
                                {"id": 2, "title": "Beta", "about": "", "right": True},
                            ],
                        }
                    ]
                }
            ]
        }
    ).encode()
    # Send browser-style RFC 7578 backslash-escaped quotes so the stored source
    # keeps literal quotes (httpx percent-encodes them instead, unlike browsers).
    boundary = "quoted-filename-boundary"
    multipart_body = (
        (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="idempotency_key"\r\n\r\n'
            "test-quoted-filename-conversion\r\n"
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="file"; filename="Prov \\"A\\".dxe"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode()
        + keyed_payload
        + f"\r\n--{boundary}--\r\n".encode()
    )
    submit_response = await client.post(
        f"{_BASE}/exam-converter/conversions",
        headers={
            **auth_headers,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        content=multipart_body,
    )

    assert submit_response.status_code == 200
    submitted = submit_response.json()
    assert submitted["status"] == "succeeded"
    job_id = submitted["job_id"]

    manifest_response = await client.get(
        f"{_BASE}/exam-converter/jobs/{job_id}/artifacts",
        headers=auth_headers,
    )
    assert manifest_response.status_code == 200
    manifest_by_key = {
        entry["artifact_key"]: entry for entry in manifest_response.json()["artifacts"]
    }
    assert manifest_by_key["examnet_pdf"]["filename"] == 'Prov "A" - Exam.net.pdf'
    assert manifest_by_key["qti_package"]["filename"] == 'Prov "A" - QTI.zip'

    pdf_response = await client.get(
        f"{_BASE}/exam-converter/jobs/{job_id}/artifacts/examnet_pdf",
        headers=auth_headers,
    )
    qti_response = await client.get(
        f"{_BASE}/exam-converter/jobs/{job_id}/artifacts/qti_package",
        headers=auth_headers,
    )
    assert pdf_response.headers["content-disposition"] == (
        "attachment; filename*=utf-8''Prov%20%22A%22%20-%20Exam.net.pdf"
    )
    assert qti_response.headers["content-disposition"] == (
        "attachment; filename*=utf-8''Prov%20%22A%22%20-%20QTI.zip"
    )


async def test_local_conversion_fails_job_when_answer_keys_are_missing(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    submit_response = await client.post(
        f"{_BASE}/exam-converter/conversions",
        headers=auth_headers,
        data={"idempotency_key": "test-unkeyed-conversion"},
        files={
            "file": (
                _DXE_FIXTURE_FILENAME,
                (_FIXTURE_DIR / _DXE_FIXTURE_FILENAME).read_bytes(),
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
        files={"file": (_DXE_FIXTURE_FILENAME, b"{}", "application/octet-stream")},
    )

    assert response.status_code == 401
