"""Public guest export admission: limiter, caller identity, size cap and runtime gate.

These tests run the real FastAPI router and prove a refused admission returns
429 without rendering, the caller key ignores User-Agent and untrusted
forwarded headers, oversized bodies are rejected, and an inactive runtime is
not found before admission.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceExportTarget,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.models import CuratedAppPublicRuntimeStatus
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.public_request_limits import (
    PublicRequestBucket,
    PublicRequestRefusal,
)
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
    make_registry,
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
    app = make_export_app(
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
    app = make_export_app(
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
