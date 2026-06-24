"""Unit tests for the scoped Document Converter API facade.

Purpose:
    Prove that the authenticated Document Converter MVP has a separate backend
    API contract under the Conversion Hub technical app id while keeping route
    activation and browser-supplied artifact authority out of scope.

Relationships:
    Exercises ``web.api.v1.apps_conversion_hub`` route functions with fake
    application handlers. Application-layer save behavior is covered by
    ``test_document_converter_artifact_saves``.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
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
    ConversionHubSubmitResult,
    ConversionHubSubmittedJob,
)
from skriptoteket.application.curated_apps.conversion_hub_saved_artifacts import (
    ConversionHubSavedVaultArtifact,
)
from skriptoteket.application.curated_apps.document_converter import (
    DocumentConverterJobStatusResult,
    DocumentConverterResultArtifact,
    SaveDocumentConverterArtifactResult,
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


def _settings(*, max_file_bytes: int = 20_000_000, max_total_bytes: int = 50_000_000) -> Settings:
    return Settings.model_construct(
        UPLOAD_MAX_FILE_BYTES=max_file_bytes,
        UPLOAD_MAX_TOTAL_BYTES=max_total_bytes,
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


class FakeCreateHandler:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def handle(self, **kwargs) -> ConversionHubSubmitResult:
        self.calls.append(kwargs)
        return ConversionHubSubmitResult(
            jobs=[
                ConversionHubSubmittedJob(
                    input_filename="source.html",
                    job_id=uuid4(),
                    status=ConversionHubJobStatus.QUEUED,
                    error=None,
                )
            ]
        )


class FakeGetDocumentConverterHandler:
    def __init__(self, result: DocumentConverterJobStatusResult) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    async def handle(self, **kwargs) -> DocumentConverterJobStatusResult:
        self.calls.append(kwargs)
        return self.result


class FakeDownloadHandler:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def handle(self, **kwargs):
        self.calls.append(kwargs)
        return ("converted.pdf", "application/pdf", b"%PDF-1.7")


class FakeSaveHandler:
    def __init__(self, result: SaveDocumentConverterArtifactResult) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    async def handle(self, **kwargs) -> SaveDocumentConverterArtifactResult:
        self.calls.append(kwargs)
        return self.result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_document_converter_routes_return_only_document_mvp_routes() -> None:
    result = await _unwrap_dishka(api.list_document_converter_routes)(
        registry=FakeRegistry(),
        user=make_user(),
    )

    route_pairs = {(route.source_format, route.output_format) for route in result.routes}
    assert route_pairs == {
        (ConversionHubSourceFormatV2.PDF, ConversionHubOutputFormatV2.MD),
        (ConversionHubSourceFormatV2.PDF, ConversionHubOutputFormatV2.DOCX),
        (ConversionHubSourceFormatV2.DOCX, ConversionHubOutputFormatV2.MD),
        (ConversionHubSourceFormatV2.DOCX, ConversionHubOutputFormatV2.PDF),
        (ConversionHubSourceFormatV2.MD, ConversionHubOutputFormatV2.PDF),
        (ConversionHubSourceFormatV2.MD, ConversionHubOutputFormatV2.DOCX),
        (ConversionHubSourceFormatV2.HTML, ConversionHubOutputFormatV2.MD),
        (ConversionHubSourceFormatV2.HTML, ConversionHubOutputFormatV2.PDF),
        (ConversionHubSourceFormatV2.HTML, ConversionHubOutputFormatV2.DOCX),
    }
    assert all(
        route.source_format
        not in {
            ConversionHubSourceFormatV2.AUDIO,
            ConversionHubSourceFormatV2.DIGIEXAM_DXE,
            ConversionHubSourceFormatV2.TRANSCRIPT_JSON,
        }
        for route in result.routes
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_document_converter_job_accepts_one_upload() -> None:
    handler = FakeCreateHandler()
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
        files=[_upload(filename="source.html", content=b"<h1>Hej</h1>", content_type="text/html")],
        wait_seconds=0,
        user=make_user(),
    )

    assert len(result.jobs) == 1
    assert result.jobs[0].input_filename == "source.html"
    assert handler.calls[0]["spec"] == spec
    uploads = cast(list[ConversionHubUpload], handler.calls[0]["uploads"])
    assert isinstance(uploads[0], ConversionHubUpload)
    assert uploads[0].filename == "source.html"
    assert uploads[0].file_bytes == b"<h1>Hej</h1>"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_document_converter_job_rejects_non_document_route() -> None:
    handler = FakeCreateHandler()

    with pytest.raises(DomainError) as excinfo:
        await _unwrap_dishka(api.submit_document_converter_job)(
            request=_request(),
            registry=FakeRegistry(),
            handler=handler,
            settings=_settings(),
            job_spec_json=ConversionHubJobSpecV2(
                source_format=ConversionHubSourceFormatV2.AUDIO,
                output_format=ConversionHubOutputFormatV2.TRANSCRIPT_BUNDLE,
            ).model_dump_json(),
            files=[_upload(filename="talk.mp3", content=b"audio", content_type="audio/mpeg")],
            wait_seconds=0,
            user=make_user(),
        )

    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR
    assert handler.calls == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_document_converter_job_rejects_mismatched_filename_suffix() -> None:
    handler = FakeCreateHandler()

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
                _upload(filename="source.pdf", content=b"<h1>Hej</h1>", content_type="text/html")
            ],
            wait_seconds=0,
            user=make_user(),
        )

    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR
    assert handler.calls == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_document_converter_job_rejects_mismatched_content_type() -> None:
    handler = FakeCreateHandler()

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
                _upload(filename="source.html", content=b"<h1>Hej</h1>", content_type="audio/mpeg")
            ],
            wait_seconds=0,
            user=make_user(),
        )

    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR
    assert handler.calls == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_document_converter_job_rejects_oversized_upload_before_handler() -> None:
    handler = FakeCreateHandler()

    with pytest.raises(DomainError) as excinfo:
        await _unwrap_dishka(api.submit_document_converter_job)(
            request=_request(),
            registry=FakeRegistry(),
            handler=handler,
            settings=_settings(max_file_bytes=4, max_total_bytes=4),
            job_spec_json=ConversionHubJobSpecV2(
                source_format=ConversionHubSourceFormatV2.HTML,
                output_format=ConversionHubOutputFormatV2.PDF,
            ).model_dump_json(),
            files=[_upload(filename="source.html", content=b"12345", content_type="text/html")],
            wait_seconds=0,
            user=make_user(),
        )

    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR
    assert handler.calls == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_document_converter_job_returns_result_artifact_after_success() -> None:
    local_job_id = uuid4()
    artifact = DocumentConverterResultArtifact(
        filename="source.pdf",
        content_type="application/pdf",
        size_bytes=None,
        sha256=None,
        source_artifact_id="document-converter:sir-job-1:converted_document",
    )
    handler = FakeGetDocumentConverterHandler(
        DocumentConverterJobStatusResult(
            job_id=local_job_id,
            status=ConversionHubJobStatus.SUCCEEDED,
            error=None,
            result_artifact=artifact,
        )
    )

    result = await _unwrap_dishka(api.get_document_converter_job_status)(
        job_id=local_job_id,
        request=_request(),
        registry=FakeRegistry(),
        handler=handler,
        user=make_user(),
    )

    assert result.result_artifact == artifact
    assert handler.calls[0]["job_id"] == local_job_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_document_converter_artifact_uses_local_job_id_only() -> None:
    handler = FakeDownloadHandler()
    local_job_id = uuid4()

    response = await _unwrap_dishka(api.download_document_converter_artifact)(
        job_id=local_job_id,
        request=_request(),
        registry=FakeRegistry(),
        handler=handler,
        user=make_user(),
    )

    assert response.media_type == "application/pdf"
    assert response.headers["Content-Disposition"] == 'attachment; filename="converted.pdf"'
    assert response.headers["Cache-Control"] == "no-store"
    assert response.body == b"%PDF-1.7"
    assert handler.calls[0]["job_id"] == local_job_id
    assert "artifact_key" not in handler.calls[0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_document_converter_artifact_uses_local_job_id_only() -> None:
    local_job_id = uuid4()
    file_id = uuid4()
    handler = FakeSaveHandler(
        SaveDocumentConverterArtifactResult(
            vault_artifact=ConversionHubSavedVaultArtifact(
                file_id=file_id,
                name="source.pdf",
                bytes=12,
                created_at=datetime(2026, 6, 23, tzinfo=timezone.utc),
            ),
            source_artifact_id="document-converter:sir-job-1:converted_document",
        )
    )

    result = await _unwrap_dishka(api.save_document_converter_artifact)(
        job_id=local_job_id,
        request=_request(),
        registry=FakeRegistry(),
        handler=handler,
        user=make_user(),
    )

    assert result.vault_artifact.file_id == file_id
    assert result.source_artifact_id == "document-converter:sir-job-1:converted_document"
    assert handler.calls[0]["job_id"] == local_job_id
    assert "artifact" not in handler.calls[0]
    assert "artifact_key" not in handler.calls[0]
