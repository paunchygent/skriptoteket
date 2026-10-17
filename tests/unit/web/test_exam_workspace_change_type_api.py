"""Thin HTTP validation and error mapping with the change-type protocol injected."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from dishka import Provider, Scope, from_context, make_async_container
from fastapi import FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace_change_type import (
    ChangeExamWorkspaceItemTypeHandlerProtocol,
    ChangeExamWorkspaceItemTypeResponse,
)
from skriptoteket.web.api.v1 import apps_conversion_hub_exam_workspace_change_type as change_api
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    source as make_source,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_parent_commands import (
    document_response,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
)
from tests.unit.web.test_apps_exam_workspace_answer_key_suggestions_api import FakeRegistry

_BASE = "/api/v1/apps/documents.conversion_hub/exam-workspace/documents/"


class ChangeTypeApiProvider(Provider):
    registry = from_context(provides=CuratedAppRegistryProtocol, scope=Scope.APP)
    command = from_context(provides=ChangeExamWorkspaceItemTypeHandlerProtocol, scope=Scope.APP)


@asynccontextmanager
async def _client(handler, actor) -> AsyncIterator[httpx.AsyncClient]:
    container = make_async_container(
        ChangeTypeApiProvider(),
        context={
            CuratedAppRegistryProtocol: FakeRegistry(),
            ChangeExamWorkspaceItemTypeHandlerProtocol: handler,
        },
    )
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(change_api.router)
    app.dependency_overrides[require_app_user_api] = lambda: actor
    setup_dishka(container, app)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client
    finally:
        await container.close()


def _body() -> dict:
    return {
        "item_id": "item_001",
        "target_kind": "free_text",
        "expected_revision": 1,
        "expected_cursor": str(uuid4()),
    }


@pytest.mark.parametrize("suggested_kind", [None, NativeExamItemKind.GAP_FILL])
async def test_http_forwards_command_and_serializes_document_and_loss_names(
    suggested_kind: NativeExamItemKind | None,
) -> None:
    actor = make_user()
    handler = AsyncMock(spec=ChangeExamWorkspaceItemTypeHandlerProtocol)
    item = make_free_text_item()
    if suggested_kind is not None:
        item = item.model_copy(
            update={
                "retry_source": make_source(label_kind=suggested_kind),
                "suggested_kind": suggested_kind,
            }
        )
    expected = ChangeExamWorkspaceItemTypeResponse(
        **document_response(make_document(item)).model_dump(),
        dropped_content=("gaps", "accepted_values"),
    )
    handler.handle.return_value = expected
    body = _body()
    lineage = expected.document.document_id
    async with _client(handler, actor) as client:
        response = await client.post(_BASE + str(lineage) + "/change-type", json=body)
    assert response.status_code == 200, response.text
    assert response.json() == expected.model_dump(mode="json")
    assert response.json()["document"]["items"][0]["suggested_kind"] == suggested_kind
    handler.handle.assert_awaited_once()
    call = handler.handle.call_args.kwargs
    assert call["actor"] == actor
    assert call["lineage_id"] == lineage
    assert call["request"].model_dump(mode="json") == body


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("target_kind", "unsupported_kind"),
        ("item_id", "invalid id"),
        ("expected_revision", 0),
        ("expected_cursor", "not-a-uuid"),
    ],
)
async def test_invalid_command_does_not_reach_handler(field: str, value: object) -> None:
    handler = AsyncMock(spec=ChangeExamWorkspaceItemTypeHandlerProtocol)
    body = {**_body(), field: value}
    async with _client(handler, make_user()) as client:
        response = await client.post(_BASE + str(uuid4()) + "/change-type", json=body)
    assert response.status_code == 422, response.text
    handler.handle.assert_not_awaited()


@pytest.mark.parametrize(
    "missing", ["expected_revision", "expected_cursor", "target_kind", "item_id"]
)
async def test_missing_precondition_or_target_is_rejected(missing: str) -> None:
    handler = AsyncMock(spec=ChangeExamWorkspaceItemTypeHandlerProtocol)
    body = _body()
    del body[missing]
    async with _client(handler, make_user()) as client:
        response = await client.post(_BASE + str(uuid4()) + "/change-type", json=body)
    assert response.status_code == 422, response.text
    handler.handle.assert_not_awaited()


@pytest.mark.parametrize(
    ("code", "status"),
    [(ErrorCode.CONFLICT, 409), (ErrorCode.NOT_FOUND, 404), (ErrorCode.VALIDATION_ERROR, 422)],
)
async def test_domain_errors_keep_their_public_code(code: ErrorCode, status: int) -> None:
    handler = AsyncMock(spec=ChangeExamWorkspaceItemTypeHandlerProtocol)
    handler.handle.side_effect = DomainError(code=code, message="Change refused")
    async with _client(handler, make_user()) as client:
        response = await client.post(_BASE + str(uuid4()) + "/change-type", json=_body())
    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == code.value
