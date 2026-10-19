"""Shared provider, fixture and builder machinery for the public export route tests.

The guest export suites reuse the command suite's admission and registry
doubles and mount the export router with the real export renderer, so each
suite file stays under the 500-line boundary without duplicating the wiring.

Test modules rebind the fixtures they need (``renderer = route_support.renderer``)
and define only their own ``app`` fixture; ``client`` is shared.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from io import BytesIO
from uuid import uuid4

import httpx
import pytest
from dishka import Provider, Scope, provide
from fastapi import FastAPI
from PIL import Image

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceExportChecklistResponse,
    ExamWorkspaceExportFile,
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
)
from skriptoteket.web.api.v1 import public_apps_exam_workspace_exports as exports_api
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
)
from tests.unit.web import (
    public_exam_workspace_command_routes_test_support as command_support,
)

admit = command_support.admit
registry = command_support.registry
client = command_support.client
make_registry = command_support.make_registry
_BASE = command_support._BASE
_CLIENT_IP = command_support._CLIENT_IP

type MultipartFile = tuple[None, str] | tuple[str, bytes, str]
"""One httpx file part: the document JSON text or one named asset payload."""

type MultipartFiles = dict[str, MultipartFile]
"""The httpx ``files`` mapping a guest request carries."""


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
    ) -> ExamWorkspaceExportFile:
        self.render_calls.append(target)
        return super().render(document=document, assets_by_id=assets_by_id, target=target)

    def checklist(
        self, *, document: NativeExamDocument, assets_by_id: Mapping[str, bytes]
    ) -> ExamWorkspaceExportChecklistResponse:
        self.checklist_calls += 1
        return super().checklist(document=document, assets_by_id=assets_by_id)


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


def make_export_app(
    *,
    registry: CuratedAppRegistryProtocol,
    admit: AdmitPublicRequestHandlerProtocol,
    renderer: RecordingRenderer,
    settings: Settings | None = None,
) -> FastAPI:
    return command_support.mount_route_app(
        provider=GuestExportProvider(
            registry=registry,
            admit=admit,
            renderer=renderer,
            settings=settings if settings is not None else Settings(),
        ),
        router=exports_api.router,
    )


@pytest.fixture
def renderer() -> RecordingRenderer:
    return RecordingRenderer()


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
) -> MultipartFiles:
    text = native_exam_document_json_bytes(document).decode("utf-8")
    files: MultipartFiles = {"document": (None, text)}
    for asset_id, payload in (assets or {}).items():
        files[f"asset:{asset_id}"] = (f"{asset_id}.png", payload, "image/png")
    return files


async def _post_export(
    client: httpx.AsyncClient,
    *,
    target: ExamWorkspaceExportTarget,
    files: MultipartFiles,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    return await client.post(
        f"{command_support._BASE}/exports/{target.value}",
        files=files,
        headers=headers or {},
    )
