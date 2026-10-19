"""Stateless public guest export routes: rendered files and the checklist.

These tests run the real FastAPI router, the real export renderer (QTI writer,
WeasyPrint PDF renderer, DOCX writer) and a fake database admission handler.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceExportTarget,
)
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.public_request_limits import PublicRequestBucket
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
)
from tests.unit.web import (
    public_exam_workspace_export_routes_test_support as route_support,
)
from tests.unit.web.public_exam_workspace_command_routes_test_support import (
    FakeAdmitHandler,
)
from tests.unit.web.public_exam_workspace_export_routes_test_support import (
    _BASE,
    _CLIENT_IP,
    RecordingRenderer,
    _multipart,
    _post_export,
    make_export_app,
)

admit = route_support.admit
registry = route_support.registry
client = route_support.client
renderer = route_support.renderer

_DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@pytest.fixture
def app(
    registry: CuratedAppRegistryProtocol,
    admit: FakeAdmitHandler,
    renderer: RecordingRenderer,
) -> FastAPI:
    return make_export_app(registry=registry, admit=admit, renderer=renderer)


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
