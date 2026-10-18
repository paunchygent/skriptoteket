"""Stateless public guest export routes: admission, asset binding, and rendering.

These tests run the real FastAPI router, the real export renderer (QTI writer,
WeasyPrint PDF renderer, DOCX writer) and a fake database admission handler.
"""

from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator, Mapping
from io import BytesIO
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI
from PIL import Image
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceExportTarget,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_export_renderer import (
    ExamWorkspaceExportRenderer,
)
from skriptoteket.application.curated_apps.handlers.public_exam_workspace_exports import (
    PublicExamWorkspaceExportHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_json import (
    native_exam_document_json_bytes,
)
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    CuratedAppPublicAccessProfile,
    CuratedAppPublicCapability,
    CuratedAppPublicRuntimeStatus,
    CuratedAppUiMode,
    curated_app_tool_id,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_writer import (  # noqa: E501
    ExamWorkspaceDocxWriter,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_pdf_renderer import (
    WeasyPrintExamNetPdfRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.public_request_limits import (
    AdmitPublicRequestHandlerProtocol,
    PublicRequestAdmission,
    PublicRequestBucket,
    PublicRequestRefusal,
)
from skriptoteket.web.api.v1 import public_apps_exam_workspace_exports as api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
)

_BASE = "/api/v1/public/apps/documents.conversion_hub/exam-converter/workspace"
_CLIENT_IP = "127.0.0.1"
_DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class FakeAdmitHandler:
    """A database-limiter double that records every admission attempt."""

    def __init__(self) -> None:
        self.calls: list[tuple[PublicRequestBucket, str]] = []
        self.refusal: PublicRequestRefusal | None = None

    async def admit(self, *, bucket: PublicRequestBucket, client_ip: str) -> PublicRequestAdmission:
        self.calls.append((bucket, client_ip))
        if self.refusal is not None:
            return PublicRequestAdmission(admitted=False, refusal=self.refusal)
        return PublicRequestAdmission(admitted=True, refusal=None)


class RecordingRenderer(ExamWorkspaceExportRenderer):
    """The real renderer plus a call log so refused requests can prove no rendering ran."""

    def __init__(self) -> None:
        super().__init__(
            qti_writer=ExamNetQtiPackageWriter(),
            pdf_renderer=WeasyPrintExamNetPdfRenderer(),
            docx_writer=ExamWorkspaceDocxWriter(),
        )
        self.render_calls: list[ExamWorkspaceExportTarget] = []
        self.checklist_calls = 0

    def render(
        self,
        *,
        document: NativeExamDocument,
        assets_by_id: Mapping[str, bytes],
        target: ExamWorkspaceExportTarget,
    ):
        self.render_calls.append(target)
        return super().render(document=document, assets_by_id=assets_by_id, target=target)

    def checklist(self, *, document: NativeExamDocument, assets_by_id: Mapping[str, bytes]):
        self.checklist_calls += 1
        return super().checklist(document=document, assets_by_id=assets_by_id)


def make_registry(
    *, runtime_status: CuratedAppPublicRuntimeStatus = CuratedAppPublicRuntimeStatus.ACTIVE
) -> CuratedAppRegistryProtocol:
    app = CuratedAppDefinition(
        app_id="documents.conversion_hub",
        tool_id=curated_app_tool_id(app_id="documents.conversion_hub"),
        app_version="app:test",
        ui_mode=CuratedAppUiMode.BESPOKE_REQUIRED,
        title="Konvertera dokument",
        summary="Konvertera DigiExam-prov.",
        min_role=Role.USER,
        public_access_profile=CuratedAppPublicAccessProfile.AUTHENTICATED_ONLY,
        public_capabilities=[
            CuratedAppPublicCapability(
                scope="exam_converter",
                profile=CuratedAppPublicAccessProfile.PUBLIC_BROWSER_RUNTIME,
                runtime_status=runtime_status,
            )
        ],
        placements=[CuratedAppPlacement(profession_slug="larare", category_slug="ovrigt")],
    )

    class Registry:
        def list_all(self) -> list[CuratedAppDefinition]:
            return [app]

        def get_by_app_id(self, *, app_id: str) -> CuratedAppDefinition | None:
            return app if app_id == "documents.conversion_hub" else None

        def get_by_tool_id(self, *, tool_id: UUID) -> CuratedAppDefinition | None:
            return app if tool_id == app.tool_id else None

    return Registry()


class GuestExportProvider(Provider):
    def __init__(
        self,
        *,
        registry: CuratedAppRegistryProtocol,
        admit: AdmitPublicRequestHandlerProtocol,
        renderer: RecordingRenderer,
        settings: Settings,
    ) -> None:
        super().__init__()
        self._registry = registry
        self._admit = admit
        self._renderer = renderer
        self._settings = settings

    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        return self._settings

    @provide(scope=Scope.APP)
    def registry(self) -> CuratedAppRegistryProtocol:
        return self._registry

    @provide(scope=Scope.APP)
    def admit_handler(self) -> AdmitPublicRequestHandlerProtocol:
        return self._admit

    @provide(scope=Scope.APP)
    def renderer(self) -> RecordingRenderer:
        return self._renderer

    @provide(scope=Scope.APP)
    def public_export_handler(
        self, renderer: RecordingRenderer
    ) -> PublicExamWorkspaceExportHandler:
        return PublicExamWorkspaceExportHandler(renderer=renderer)


def make_app(
    *,
    registry: CuratedAppRegistryProtocol,
    admit: AdmitPublicRequestHandlerProtocol,
    renderer: RecordingRenderer,
    settings: Settings | None = None,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(api.router)
    container = make_async_container(
        GuestExportProvider(
            registry=registry,
            admit=admit,
            renderer=renderer,
            settings=settings if settings is not None else Settings(),
        )
    )
    setup_dishka(container, app)
    return app


@pytest.fixture
def admit() -> FakeAdmitHandler:
    return FakeAdmitHandler()


@pytest.fixture
def renderer() -> RecordingRenderer:
    return RecordingRenderer()


@pytest.fixture
def registry() -> CuratedAppRegistryProtocol:
    return make_registry()


@pytest.fixture
def app(
    registry: CuratedAppRegistryProtocol, admit: FakeAdmitHandler, renderer: RecordingRenderer
) -> FastAPI:
    return make_app(registry=registry, admit=admit, renderer=renderer)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


def _png() -> bytes:
    buffer = BytesIO()
    Image.new("RGBA", (8, 4), (25, 130, 60, 180)).save(buffer, format="PNG")
    return buffer.getvalue()


def _picture_document() -> tuple[NativeExamDocument, str, bytes]:
    payload = _png()
    digest = hashlib.sha256(payload).hexdigest()
    asset_id = f"asset_{digest[:16]}"
    item = make_free_text_item().model_copy(
        update={
            "body": (
                NativeParagraph(
                    heading_level=None,
                    segments=(
                        NativeTextSegment(text="Betrakta: ", marks=()),
                        NativeAssetSegment(asset_id=asset_id),
                    ),
                ),
            )
        }
    )
    document = NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Omprov: grammatik",
        items=(item,),
        assets=(
            NativeExamAsset(
                asset_id=asset_id,
                sha256=digest,
                media_type="image/png",
                byte_length=len(payload),
            ),
        ),
        origin=NativeExamDocumentOrigin(kind="created"),
    )
    return document, asset_id, payload


def _multipart(
    document: NativeExamDocument, assets: Mapping[str, bytes] | None = None
) -> dict[str, Any]:
    text = native_exam_document_json_bytes(document).decode("utf-8")
    files: dict[str, Any] = {"document": (None, text)}
    for asset_id, payload in (assets or {}).items():
        files[f"asset:{asset_id}"] = (f"{asset_id}.png", payload, "image/png")
    return files


async def _post_export(
    client: httpx.AsyncClient,
    *,
    target: ExamWorkspaceExportTarget,
    files: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    return await client.post(
        f"{_BASE}/exports/{target.value}",
        files=files,
        headers=headers or {},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "target,media_type,suffix,prefix",
    [
        (ExamWorkspaceExportTarget.QTI, "application/zip", ".zip", b"PK"),
        (ExamWorkspaceExportTarget.PDF, "application/pdf", ".pdf", b"%PDF"),
        (ExamWorkspaceExportTarget.DOCX, _DOCX_MEDIA_TYPE, ".docx", b"PK"),
    ],
)
async def test_guest_export_without_auth_returns_the_rendered_file(
    client: httpx.AsyncClient,
    admit: FakeAdmitHandler,
    target: ExamWorkspaceExportTarget,
    media_type: str,
    suffix: str,
    prefix: bytes,
) -> None:
    response = await _post_export(
        client, target=target, files=_multipart(make_document(make_free_text_item()))
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == media_type
    assert response.headers["content-disposition"] == (
        f'attachment; filename="Omprov grammatik{suffix}"'
    )
    assert response.content.startswith(prefix)
    assert response.headers.get("set-cookie") is None
    assert admit.calls == [(PublicRequestBucket.GUEST_EXPORT, _CLIENT_IP)]


@pytest.mark.asyncio
async def test_guest_checklist_returns_the_wire_shape(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        f"{_BASE}/export-checklist",
        files=_multipart(make_document(make_free_text_item())),
    )

    assert response.status_code == 200
    assert response.json() == {"entries": [], "inline_choice_min_options": 2}


@pytest.mark.asyncio
async def test_missing_declared_asset_part_is_a_validation_error(
    client: httpx.AsyncClient,
) -> None:
    document, asset_id, _payload = _picture_document()

    response = await _post_export(
        client, target=ExamWorkspaceExportTarget.QTI, files=_multipart(document)
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"] == {
        "reason": "asset_mismatch",
        "asset_id": asset_id,
    }


@pytest.mark.asyncio
async def test_wrong_asset_bytes_are_a_validation_error(
    client: httpx.AsyncClient,
) -> None:
    document, asset_id, _payload = _picture_document()

    response = await _post_export(
        client,
        target=ExamWorkspaceExportTarget.QTI,
        files=_multipart(document, {asset_id: b"not the declared picture"}),
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"] == {
        "reason": "asset_mismatch",
        "asset_id": asset_id,
    }


@pytest.mark.asyncio
async def test_extra_undeclared_asset_part_is_a_validation_error(
    client: httpx.AsyncClient,
) -> None:
    response = await _post_export(
        client,
        target=ExamWorkspaceExportTarget.QTI,
        files=_multipart(make_document(make_free_text_item()), {"asset_extra": b"x"}),
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"] == {
        "reason": "asset_mismatch",
        "asset_id": "asset_extra",
    }


@pytest.mark.asyncio
async def test_declared_asset_renders_when_bytes_match(
    client: httpx.AsyncClient,
) -> None:
    document, asset_id, payload = _picture_document()

    response = await _post_export(
        client,
        target=ExamWorkspaceExportTarget.PDF,
        files=_multipart(document, {asset_id: payload}),
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_blocked_document_refuses_after_admission(
    client: httpx.AsyncClient, admit: FakeAdmitHandler
) -> None:
    blocked = make_document(make_free_text_item()).model_copy(update={"title": "!!!"})

    response = await _post_export(
        client, target=ExamWorkspaceExportTarget.QTI, files=_multipart(blocked)
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"]["blockers"] == [
        {"item_id": None, "reason": "title_without_text"}
    ]
    assert admit.calls == [(PublicRequestBucket.GUEST_EXPORT, _CLIENT_IP)]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "refusal", [PublicRequestRefusal.CALLER_LIMIT, PublicRequestRefusal.POOL_LIMIT]
)
async def test_refused_admission_returns_429_and_never_renders(
    client: httpx.AsyncClient,
    admit: FakeAdmitHandler,
    renderer: RecordingRenderer,
    refusal: PublicRequestRefusal,
) -> None:
    admit.refusal = refusal

    response = await _post_export(
        client,
        target=ExamWorkspaceExportTarget.QTI,
        files=_multipart(make_document(make_free_text_item())),
    )

    assert response.status_code == 429
    assert response.json()["error"]["details"] == {
        "reason": refusal.value,
        "bucket": PublicRequestBucket.GUEST_EXPORT.value,
    }
    assert renderer.render_calls == []
    assert renderer.checklist_calls == 0


@pytest.mark.asyncio
async def test_user_agent_never_changes_the_caller_key(
    client: httpx.AsyncClient, admit: FakeAdmitHandler
) -> None:
    document = make_document(make_free_text_item())

    first = await _post_export(
        client,
        target=ExamWorkspaceExportTarget.QTI,
        files=_multipart(document),
        headers={"User-Agent": "first-agent"},
    )
    second = await _post_export(
        client,
        target=ExamWorkspaceExportTarget.QTI,
        files=_multipart(document),
        headers={"User-Agent": "second-agent"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert [call[1] for call in admit.calls] == [_CLIENT_IP, _CLIENT_IP]


@pytest.mark.asyncio
async def test_untrusted_forwarded_for_header_does_not_change_the_caller_key(
    client: httpx.AsyncClient, admit: FakeAdmitHandler
) -> None:
    response = await _post_export(
        client,
        target=ExamWorkspaceExportTarget.QTI,
        files=_multipart(make_document(make_free_text_item())),
        headers={"X-Forwarded-For": "203.0.113.9"},
    )

    assert response.status_code == 200
    assert admit.calls == [(PublicRequestBucket.GUEST_EXPORT, _CLIENT_IP)]


@pytest.mark.asyncio
async def test_oversized_request_is_rejected_before_rendering(
    admit: FakeAdmitHandler, renderer: RecordingRenderer
) -> None:
    app = make_app(
        registry=make_registry(),
        admit=admit,
        renderer=renderer,
        settings=Settings(PUBLIC_GUEST_EXAM_MAX_REQUEST_BYTES=64),
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as limited:
        response = await limited.post(
            f"{_BASE}/exports/qti",
            files=_multipart(make_document(make_free_text_item())),
        )

    assert response.status_code == 413
    assert response.json()["error"]["details"]["reason"] == "payload_too_large"
    assert renderer.render_calls == []


@pytest.mark.asyncio
async def test_inactive_runtime_is_not_found_before_admission(
    admit: FakeAdmitHandler, renderer: RecordingRenderer
) -> None:
    app = make_app(
        registry=make_registry(runtime_status=CuratedAppPublicRuntimeStatus.CONTRACT_ONLY),
        admit=admit,
        renderer=renderer,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as inactive:
        response = await inactive.post(
            f"{_BASE}/exports/qti",
            files=_multipart(make_document(make_free_text_item())),
        )

    assert response.status_code == 404
    assert admit.calls == []
    assert renderer.render_calls == []
