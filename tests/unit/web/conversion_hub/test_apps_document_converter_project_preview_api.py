"""Document Converter project preview API contract tests.

Purpose:
    Prove the HTML/CSS project preview contract lives under the scoped
    Conversion Hub Document Converter namespace without activating the
    route-visible app.

Relationships:
    Exercises the thin FastAPI route functions with fake application handlers.
    Application lifecycle and infrastructure sandbox behavior are covered by
    adjacent project preview tests.
"""

from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.datastructures import Headers, UploadFile
from starlette.requests import Request

from skriptoteket.application.curated_apps.conversion_hub_saved_artifacts import (
    ConversionHubSavedVaultArtifact,
)
from skriptoteket.application.curated_apps.document_converter import (
    DocumentConverterStoredArtifact,
)
from skriptoteket.application.curated_apps.document_converter_projects import (
    DiscardDocumentConverterProjectPreviewResult,
    DocumentConverterProjectManifest,
    DocumentConverterProjectOutputMode,
    DocumentConverterProjectPreviewArtifact,
    DocumentConverterProjectPreviewArtifactKind,
    DocumentConverterProjectPreviewResult,
    DocumentConverterProjectPreviewStatus,
    DocumentConverterProjectUploadedFile,
    SaveDocumentConverterProjectPreviewArtifactResult,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.web.api.v1 import (
    apps_conversion_hub_document_converter_project_previews as api,
)
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


def test_project_preview_download_openapi_contract_is_pdf_binary() -> None:
    app = FastAPI()
    app.include_router(api.router)
    client = TestClient(app)
    schema = client.get("/openapi.json").json()

    response_content = schema["paths"][
        "/api/v1/apps/documents.conversion_hub/document-converter/project-previews/"
        "{preview_id}/artifacts/{artifact_id}"
    ]["get"]["responses"]["200"]["content"]

    assert response_content == {
        "application/pdf": {"schema": {"type": "string", "format": "binary"}}
    }


def _manifest_json() -> str:
    return """{
      "html_entries": [
        {"entry_id": "worksheet", "filename": "worksheet.html", "title": "Worksheet"}
      ],
      "css_files": ["style.css"],
      "image_files": ["logo.png"],
      "font_files": [],
      "output_mode": "combined_pdf",
      "pdf_controls": {
        "paper_size": "a4",
        "orientation": "portrait",
        "margins": {
          "top_mm": 12,
          "right_mm": 12,
          "bottom_mm": 12,
          "left_mm": 12
        },
        "template_id": "academic_phd"
      }
    }"""


class FakeRegistry:
    def get_by_app_id(self, *, app_id: str):
        return SimpleNamespace(app_id=app_id, min_role=Role.USER)


class FakeRenderPreviewHandler:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def handle(self, **kwargs) -> DocumentConverterProjectPreviewResult:
        self.calls.append(kwargs)
        return _preview_result()


class FakeGetPreviewHandler:
    async def handle(self, **kwargs) -> DocumentConverterProjectPreviewResult:
        return _preview_result(preview_id=cast(object, kwargs["preview_id"]))


class FakeDownloadPreviewArtifactHandler:
    def __init__(self, *, filename: str = "preview.pdf") -> None:
        self.filename = filename
        self.calls: list[dict[str, object]] = []

    async def handle(self, **kwargs) -> DocumentConverterStoredArtifact:
        self.calls.append(kwargs)
        return DocumentConverterStoredArtifact(
            filename=self.filename,
            content_type="application/pdf",
            content=b"%PDF-PREVIEW",
        )


class FakeSavePreviewArtifactHandler:
    def __init__(self, *, filename: str = "preview.pdf") -> None:
        self.filename = filename
        self.calls: list[dict[str, object]] = []

    async def handle(self, **kwargs) -> SaveDocumentConverterProjectPreviewArtifactResult:
        self.calls.append(kwargs)
        return SaveDocumentConverterProjectPreviewArtifactResult(
            vault_artifact=ConversionHubSavedVaultArtifact(
                file_id=uuid4(),
                name=self.filename,
                bytes=12,
                created_at=datetime(2026, 6, 25, tzinfo=timezone.utc),
            ),
            source_artifact_id="document-converter:project-preview:preview:artifact",
        )


class FakeDiscardPreviewHandler:
    async def handle(self, **kwargs) -> DiscardDocumentConverterProjectPreviewResult:
        return DiscardDocumentConverterProjectPreviewResult(
            preview_id=cast(object, kwargs["preview_id"]),
            status=DocumentConverterProjectPreviewStatus.DISCARDED,
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_render_project_preview_accepts_scoped_html_css_project() -> None:
    handler = FakeRenderPreviewHandler()

    result = await _unwrap_dishka(api.render_document_converter_project_preview)(
        request=_request(),
        registry=FakeRegistry(),
        handler=handler,
        settings=_settings(),
        manifest_json=_manifest_json(),
        files=[
            _upload(filename="worksheet.html", content=b"<h1>Hi</h1>", content_type="text/html"),
            _upload(filename="style.css", content=b"h1{}", content_type="text/css"),
            _upload(filename="logo.png", content=b"png", content_type="image/png"),
        ],
        user=make_user(),
    )

    assert result.status is DocumentConverterProjectPreviewStatus.SUCCEEDED
    assert result.output_mode is DocumentConverterProjectOutputMode.COMBINED_PDF
    manifest = cast(DocumentConverterProjectManifest, handler.calls[0]["manifest"])
    assert manifest.output_mode is DocumentConverterProjectOutputMode.COMBINED_PDF
    uploads = cast(list[DocumentConverterProjectUploadedFile], handler.calls[0]["files"])
    assert [upload.filename for upload in uploads] == ["worksheet.html", "style.css", "logo.png"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_render_project_preview_rejects_undeclared_upload_before_handler() -> None:
    handler = FakeRenderPreviewHandler()

    with pytest.raises(DomainError) as excinfo:
        await _unwrap_dishka(api.render_document_converter_project_preview)(
            request=_request(),
            registry=FakeRegistry(),
            handler=handler,
            settings=_settings(),
            manifest_json=_manifest_json(),
            files=[
                _upload(
                    filename="worksheet.html",
                    content=b"<h1>Hi</h1>",
                    content_type="text/html",
                ),
                _upload(filename="style.css", content=b"h1{}", content_type="text/css"),
                _upload(filename="evil.png", content=b"png", content_type="image/png"),
            ],
            user=make_user(),
        )

    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR
    assert handler.calls == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_project_preview_artifact_uses_server_ids_only() -> None:
    preview_id = uuid4()
    artifact_id = uuid4()
    handler = FakeDownloadPreviewArtifactHandler(filename="Backendens projekt.pdf")

    response = await _unwrap_dishka(api.download_document_converter_project_preview_artifact)(
        preview_id=preview_id,
        artifact_id=artifact_id,
        registry=FakeRegistry(),
        handler=handler,
        filename_stem="Lärarens projekt.pdf",
        user=make_user(),
    )

    assert response.body == b"%PDF-PREVIEW"
    assert response.headers["Content-Disposition"] == (
        'attachment; filename="Backendens projekt.pdf"'
    )
    assert handler.calls[0]["preview_id"] == preview_id
    assert handler.calls[0]["artifact_id"] == artifact_id
    assert handler.calls[0]["filename_stem"] == "Lärarens projekt.pdf"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_project_preview_artifact_requires_explicit_server_owned_artifact() -> None:
    preview_id = uuid4()
    artifact_id = uuid4()
    handler = FakeSavePreviewArtifactHandler(filename="Backendens projekt.pdf")

    result = await _unwrap_dishka(api.save_document_converter_project_preview_artifact)(
        preview_id=preview_id,
        artifact_id=artifact_id,
        registry=FakeRegistry(),
        handler=handler,
        filename_stem="Lärarens projekt.pdf",
        user=make_user(),
    )

    assert result.vault_artifact.name == "Backendens projekt.pdf"
    assert handler.calls[0]["preview_id"] == preview_id
    assert handler.calls[0]["artifact_id"] == artifact_id
    assert handler.calls[0]["filename_stem"] == "Lärarens projekt.pdf"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_discard_project_preview_uses_preview_id_only() -> None:
    preview_id = uuid4()

    result = await _unwrap_dishka(api.discard_document_converter_project_preview)(
        preview_id=preview_id,
        registry=FakeRegistry(),
        handler=FakeDiscardPreviewHandler(),
        user=make_user(),
    )

    assert result.preview_id == preview_id
    assert result.status is DocumentConverterProjectPreviewStatus.DISCARDED


def _preview_result(preview_id: object | None = None) -> DocumentConverterProjectPreviewResult:
    artifact_id = uuid4()
    created_at = datetime(2026, 6, 25, tzinfo=timezone.utc)
    return DocumentConverterProjectPreviewResult(
        preview_id=cast(UUID, preview_id) if preview_id is not None else uuid4(),
        status=DocumentConverterProjectPreviewStatus.SUCCEEDED,
        output_mode=DocumentConverterProjectOutputMode.COMBINED_PDF,
        created_at=created_at,
        expires_at=created_at + timedelta(hours=24),
        artifacts=[
            DocumentConverterProjectPreviewArtifact(
                artifact_id=artifact_id,
                kind=DocumentConverterProjectPreviewArtifactKind.COMBINED_PDF,
                filename="preview.pdf",
                content_type="application/pdf",
                size_bytes=12,
                source_entry_id=None,
                download_url=None,
            )
        ],
        template_id="academic_phd",
        error=None,
    )
