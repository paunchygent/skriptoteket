"""Unit coverage for the Conversion Hub API routes."""

from __future__ import annotations

import io
from types import SimpleNamespace
from uuid import uuid4

import pytest
from starlette.datastructures import UploadFile
from starlette.requests import Request

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJobSpecV2,
    ConversionHubJobStatus,
    ConversionHubJobStatusResult,
    ConversionHubOutputFormatV2,
    ConversionHubPdfLayoutV2,
    ConversionHubSourceFormatV2,
    ConversionHubSubmitResult,
    ConversionHubSubmittedJob,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import ConversionHubUpload
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.web.api.v1 import apps_conversion_hub as api
from tests.fixtures.identity_fixtures import make_user


def _unwrap_dishka(fn):
    return getattr(fn, "__dishka_orig_func__", fn)


def _request() -> Request:
    request = Request({"type": "http", "headers": []})
    request.state.correlation_id = uuid4()
    return request


class FakeRegistry:
    def get_by_app_id(self, *, app_id: str):
        return SimpleNamespace(app_id=app_id, min_role=Role.USER)


class FakeCreateHandler:
    def __init__(self, result: ConversionHubSubmitResult) -> None:
        self.result = result
        self.captured_uploads: list[ConversionHubUpload] = []
        self.calls = 0

    async def handle(self, **kwargs) -> ConversionHubSubmitResult:
        self.calls += 1
        self.captured_uploads = kwargs["uploads"]
        return self.result


class FakeGetHandler:
    def __init__(self, result: ConversionHubJobStatusResult) -> None:
        self.result = result

    async def handle(self, **kwargs) -> ConversionHubJobStatusResult:
        return self.result


class FakeDownloadHandler:
    async def handle(self, **kwargs):
        return ("converted.pdf", "application/pdf", b"%PDF-1.7")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_jobs_returns_local_job_ids_from_handler() -> None:
    user = make_user()
    local_job_id = uuid4()
    handler = FakeCreateHandler(
        ConversionHubSubmitResult(
            jobs=[
                ConversionHubSubmittedJob(
                    input_filename="in.html",
                    job_id=local_job_id,
                    status=ConversionHubJobStatus.QUEUED,
                    error=None,
                )
            ]
        )
    )

    result = await _unwrap_dishka(api.submit_jobs)(
        request=_request(),
        registry=FakeRegistry(),
        handler=handler,
        job_spec_json=ConversionHubJobSpecV2(
            source_format=ConversionHubSourceFormatV2.HTML,
            output_format=ConversionHubOutputFormatV2.PDF,
        ).model_dump_json(),
        files=[UploadFile(filename="in.html", file=io.BytesIO(b"<h1>Hej</h1>"))],
        wait_seconds=0,
        user=user,
        _=None,
    )

    assert result.jobs[0].job_id == local_job_id
    assert result.jobs[0].status is ConversionHubJobStatus.QUEUED


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_job_status_returns_owned_local_job_status() -> None:
    user = make_user()
    local_job_id = uuid4()
    handler = FakeGetHandler(
        ConversionHubJobStatusResult(
            job_id=local_job_id,
            status=ConversionHubJobStatus.SUCCEEDED,
            error=None,
        )
    )

    result = await _unwrap_dishka(api.get_job_status)(
        job_id=local_job_id,
        request=_request(),
        registry=FakeRegistry(),
        handler=handler,
        user=user,
    )

    assert result.job_id == local_job_id
    assert result.status is ConversionHubJobStatus.SUCCEEDED


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_artifact_returns_proxy_attachment_response() -> None:
    user = make_user()

    response = await _unwrap_dishka(api.download_artifact)(
        job_id=uuid4(),
        request=_request(),
        registry=FakeRegistry(),
        handler=FakeDownloadHandler(),
        user=user,
    )

    assert response.media_type == "application/pdf"
    assert response.headers["Content-Disposition"] == 'attachment; filename="converted.pdf"'
    assert response.headers["Cache-Control"] == "no-store"
    assert response.body == b"%PDF-1.7"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_jobs_rejects_wait_seconds_above_upstream_cap() -> None:
    user = make_user()
    handler = FakeCreateHandler(ConversionHubSubmitResult(jobs=[]))

    with pytest.raises(DomainError) as excinfo:
        await _unwrap_dishka(api.submit_jobs)(
            request=_request(),
            registry=FakeRegistry(),
            handler=handler,
            job_spec_json=ConversionHubJobSpecV2(
                source_format=ConversionHubSourceFormatV2.HTML,
                output_format=ConversionHubOutputFormatV2.MD,
            ).model_dump_json(),
            files=[UploadFile(filename="in.html", file=io.BytesIO(b"<p>Hej</p>"))],
            wait_seconds=21,
            user=user,
            _=None,
        )

    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_jobs_rejects_invalid_pdf_layout_before_handler_call() -> None:
    user = make_user()
    handler = FakeCreateHandler(ConversionHubSubmitResult(jobs=[]))

    with pytest.raises(DomainError) as excinfo:
        await _unwrap_dishka(api.submit_jobs)(
            request=_request(),
            registry=FakeRegistry(),
            handler=handler,
            job_spec_json=ConversionHubJobSpecV2(
                source_format=ConversionHubSourceFormatV2.HTML,
                output_format=ConversionHubOutputFormatV2.MD,
                pdf_layout=ConversionHubPdfLayoutV2(),
            ).model_dump_json(),
            files=[UploadFile(filename="in.html", file=io.BytesIO(b"<p>Hej</p>"))],
            wait_seconds=0,
            user=user,
            _=None,
        )

    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR
    assert handler.calls == 0
