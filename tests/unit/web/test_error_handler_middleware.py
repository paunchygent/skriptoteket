from __future__ import annotations

from typing import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI

from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.web.middleware.error_handler import error_handler_middleware


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
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
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
