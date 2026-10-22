"""A try-again answer carries the door's Retry-After as a header."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.web.middleware.error_handler import error_handler_middleware


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)

    def raising(code: ErrorCode, details: dict[str, object]) -> None:
        raise DomainError(code=code, message="Försök igen", details=details)

    @app.get("/with-retry-after")
    async def with_retry_after() -> None:
        raising(ErrorCode.AI_TRY_AGAIN, {"retry_after_seconds": 7})

    @app.get("/without-retry-after")
    async def without_retry_after() -> None:
        raising(ErrorCode.AI_TRY_AGAIN, {})

    @app.get("/unparsed-retry-after")
    async def unparsed_retry_after() -> None:
        raising(ErrorCode.AI_TRY_AGAIN, {"retry_after_seconds": "soon"})

    @app.get("/other-error")
    async def other_error() -> None:
        raising(ErrorCode.VALIDATION_ERROR, {"retry_after_seconds": 7})

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


async def test_a_try_again_error_with_retry_after_sets_the_header(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/with-retry-after")

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "7"
    assert response.json()["error"]["details"] == {"retry_after_seconds": 7}


@pytest.mark.parametrize("path", ["/without-retry-after", "/unparsed-retry-after", "/other-error"])
async def test_no_header_without_a_numeric_retry_after_on_a_try_again_error(
    client: httpx.AsyncClient, path: str
) -> None:
    response = await client.get(path)

    assert "Retry-After" not in response.headers
