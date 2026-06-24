"""Document Converter batch API contract tests.

Purpose:
    Prove the route-inactive Document Converter API accepts validated batches
    under the scoped Conversion Hub namespace without exposing route-visible UI
    or browser-authored artifact authority.

Relationships:
    Exercises ``web.api.v1.apps_conversion_hub`` with fake application
    handlers; producer routing behavior is covered by
    ``test_document_converter_producer_routing``.
"""

from __future__ import annotations

import io
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from starlette.datastructures import Headers, UploadFile
from starlette.requests import Request

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJobSpecV2,
    ConversionHubJobStatus,
    ConversionHubOutputFormatV2,
    ConversionHubSourceFormatV2,
)
from skriptoteket.application.curated_apps.document_converter import (
    DocumentConverterProducerKind,
    DocumentConverterSubmitResult,
    DocumentConverterSubmittedJob,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import (
    ConversionHubUpload,
)
from skriptoteket.config import Settings
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


def _settings() -> Settings:
    return Settings.model_construct(
        UPLOAD_MAX_FILE_BYTES=20_000_000,
        UPLOAD_MAX_TOTAL_BYTES=50_000_000,
    )


def _upload(*, filename: str, content: bytes, content_type: str) -> UploadFile:
    return UploadFile(
        filename=filename,
        file=io.BytesIO(content),
        headers=Headers({"content-type": content_type}),
    )


class FakeRegistry:
    def get_by_app_id(self, *, app_id: str):
        return SimpleNamespace(app_id=app_id, min_role=Role.USER)


class FakeDocumentConverterSubmitHandler:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def handle(self, **kwargs) -> DocumentConverterSubmitResult:
        self.calls.append(kwargs)
        uploads = cast(list[ConversionHubUpload], kwargs["uploads"])
        return DocumentConverterSubmitResult(
            jobs=[
                DocumentConverterSubmittedJob(
                    input_filename=upload.filename,
                    job_id=uuid4(),
                    status=ConversionHubJobStatus.SUCCEEDED,
                    error=None,
                    producer=DocumentConverterProducerKind.LOCAL,
                    producer_reason="local_html_to_pdf",
                )
                for upload in uploads
            ]
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_document_converter_jobs_accepts_general_batch_up_to_ten() -> None:
    handler = FakeDocumentConverterSubmitHandler()
    spec = ConversionHubJobSpecV2(
        source_format=ConversionHubSourceFormatV2.HTML,
        output_format=ConversionHubOutputFormatV2.PDF,
    )

    result = await _unwrap_dishka(api.submit_document_converter_job)(
        request=_request(),
        registry=FakeRegistry(),
        handler=handler,
        settings=_settings(),
        job_spec_json=spec.model_dump_json(),
        files=[
            _upload(filename="one.html", content=b"<h1>One</h1>", content_type="text/html"),
            _upload(filename="two.html", content=b"<h1>Two</h1>", content_type="text/html"),
        ],
        wait_seconds=0,
        user=make_user(),
    )

    assert [job.input_filename for job in result.jobs] == ["one.html", "two.html"]
    assert {job.producer for job in result.jobs} == {DocumentConverterProducerKind.LOCAL}
    uploads = cast(list[ConversionHubUpload], handler.calls[0]["uploads"])
    assert [upload.filename for upload in uploads] == ["one.html", "two.html"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_document_converter_jobs_rejects_more_than_ten_items() -> None:
    handler = FakeDocumentConverterSubmitHandler()

    with pytest.raises(DomainError) as excinfo:
        await _unwrap_dishka(api.submit_document_converter_job)(
            request=_request(),
            registry=FakeRegistry(),
            handler=handler,
            settings=_settings(),
            job_spec_json=ConversionHubJobSpecV2(
                source_format=ConversionHubSourceFormatV2.HTML,
                output_format=ConversionHubOutputFormatV2.PDF,
            ).model_dump_json(),
            files=[
                _upload(
                    filename=f"source-{index}.html",
                    content=b"<h1>Hej</h1>",
                    content_type="text/html",
                )
                for index in range(11)
            ],
            wait_seconds=0,
            user=make_user(),
        )

    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR
    assert "at most 10" in excinfo.value.message
    assert excinfo.value.details["max_items"] == 10
    assert handler.calls == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_document_converter_jobs_rejects_mixed_invalid_batch_before_handler() -> None:
    handler = FakeDocumentConverterSubmitHandler()

    with pytest.raises(DomainError) as excinfo:
        await _unwrap_dishka(api.submit_document_converter_job)(
            request=_request(),
            registry=FakeRegistry(),
            handler=handler,
            settings=_settings(),
            job_spec_json=ConversionHubJobSpecV2(
                source_format=ConversionHubSourceFormatV2.HTML,
                output_format=ConversionHubOutputFormatV2.PDF,
            ).model_dump_json(),
            files=[
                _upload(filename="source.html", content=b"<h1>Hej</h1>", content_type="text/html"),
                _upload(filename="notes.pdf", content=b"%PDF-1.7", content_type="application/pdf"),
            ],
            wait_seconds=0,
            user=make_user(),
        )

    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR
    assert excinfo.value.details["filename"] == "notes.pdf"
    assert handler.calls == []
