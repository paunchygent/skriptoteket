"""Error handler middleware tests.

Purpose:
    Verify that the central web error boundary preserves safe JSON responses
    and records local RBAC denials without requiring route-specific hooks.

Relationships:
    - Exercises `skriptoteket.web.middleware.error_handler`.
    - Uses a tiny Dishka-container stub for auth outcome recorder resolution.
"""

from __future__ import annotations

from typing import AsyncIterator
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI, Request

from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.identity.role_guards import require_any_role
from skriptoteket.protocols.auth_outcomes import AuthOutcomeRecorderProtocol
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.identity_fixtures import make_user
from tests.fixtures.profile_app_continuation_support import AuthOutcomeRecorderStub


class AuthOutcomeContainerStub:
    def __init__(self, recorder: AuthOutcomeRecorderStub) -> None:
        self._recorder = recorder

    async def get(self, dependency_type: object) -> AuthOutcomeRecorderProtocol:
        assert dependency_type is AuthOutcomeRecorderProtocol
        return self._recorder


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)

    @app.get("/boom-domain")
    async def boom_domain() -> None:
        raise not_found("Tool", "123")

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    @app.get("/api/boom-domain")
    async def api_boom_domain() -> None:
        raise DomainError(code=ErrorCode.VALIDATION_ERROR, message="Bad", details={"field": "x"})

    @app.get("/api/boom")
    async def api_boom() -> None:
        raise RuntimeError("boom")

    return app


@pytest.fixture
def auth_outcomes() -> AuthOutcomeRecorderStub:
    return AuthOutcomeRecorderStub()


@pytest.fixture
def app_with_recorder(auth_outcomes: AuthOutcomeRecorderStub) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)

    @app.get("/api/v1/editor/rbac-denied")
    async def rbac_denied(request: Request) -> None:
        request.state.correlation_id = UUID("f6dd6fc8-8ae4-42a8-864e-9df1d72c1c9f")
        request.state.dishka_container = AuthOutcomeContainerStub(auth_outcomes)
        require_any_role(
            user=make_user(role=Role.CONTRIBUTOR),
            roles=(Role.ADMIN, Role.SUPERUSER),
        )

    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


@pytest.fixture
async def client_with_recorder(app_with_recorder: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app_with_recorder),
        base_url="http://test",
    ) as c:
        yield c


@pytest.mark.unit
@pytest.mark.asyncio
async def test_domain_error_returns_json_for_api_routes(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/boom-domain")
    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == ErrorCode.VALIDATION_ERROR.value
    assert payload["error"]["details"]["field"] == "x"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_domain_error_returns_json_when_accepts_json(client: httpx.AsyncClient) -> None:
    response = await client.get("/boom-domain", headers={"accept": "application/json"})
    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == ErrorCode.NOT_FOUND.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_domain_error_returns_json_for_browser_requests(client: httpx.AsyncClient) -> None:
    response = await client.get("/boom-domain")
    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == ErrorCode.NOT_FOUND.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_unhandled_exception_returns_safe_500_json(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/boom")
    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["code"] == ErrorCode.INTERNAL_ERROR.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_unhandled_exception_returns_safe_500_json_for_browser_requests(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/boom")
    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["code"] == ErrorCode.INTERNAL_ERROR.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_forbidden_role_guard_records_rbac_denial_from_error_boundary(
    client_with_recorder: httpx.AsyncClient,
    auth_outcomes: AuthOutcomeRecorderStub,
) -> None:
    correlation_id = UUID("f6dd6fc8-8ae4-42a8-864e-9df1d72c1c9f")

    response = await client_with_recorder.get("/api/v1/editor/rbac-denied")

    assert response.status_code == 403
    details = response.json()["error"]["details"]
    assert set(details["required_roles"]) == {"admin", "superuser"}
    assert details["actual_role"] == "contributor"
    assert auth_outcomes.rbac_decisions == [
        ("denied", "admin_or_superuser", "contributor", "editor", correlation_id)
    ]
