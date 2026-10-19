"""Public guest export validation: asset binding and blocked documents.

These tests run the real FastAPI router and assert the contracted 422 shapes
when asset parts are missing, mismatched or undeclared, or the document has
export blockers.
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
    _CLIENT_IP,
    RecordingRenderer,
    _multipart,
    _picture_document,
    _post_export,
    make_export_app,
)

admit = route_support.admit
registry = route_support.registry
client = route_support.client
renderer = route_support.renderer


@pytest.fixture
def app(
    registry: CuratedAppRegistryProtocol,
    admit: FakeAdmitHandler,
    renderer: RecordingRenderer,
) -> FastAPI:
    return make_export_app(registry=registry, admit=admit, renderer=renderer)


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
