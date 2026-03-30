from __future__ import annotations

from collections.abc import AsyncIterator
from typing import cast
from unittest.mock import AsyncMock

import httpx
import pytest
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.application.identity.commands import (
    RequestPasswordResetResult,
    ResetPasswordResult,
)
from skriptoteket.application.identity.handlers.request_password_reset import (
    RequestPasswordResetHandlerProtocol,
)
from skriptoteket.application.identity.handlers.reset_password import ResetPasswordHandlerProtocol
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.web.api.v1 import auth as auth_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware


class PasswordResetApiProvider(Provider):
    def __init__(
        self,
        *,
        settings: Settings,
        request_handler: AsyncMock,
        reset_handler: AsyncMock,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._request_handler = request_handler
        self._reset_handler = reset_handler

    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        return self._settings

    @provide(scope=Scope.REQUEST)
    def request_password_reset_handler(self) -> RequestPasswordResetHandlerProtocol:
        return cast(RequestPasswordResetHandlerProtocol, self._request_handler)

    @provide(scope=Scope.REQUEST)
    def reset_password_handler(self) -> ResetPasswordHandlerProtocol:
        return cast(ResetPasswordHandlerProtocol, self._reset_handler)


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def request_handler() -> AsyncMock:
    mock = AsyncMock(spec=RequestPasswordResetHandlerProtocol)
    mock.handle.return_value = RequestPasswordResetResult()
    return mock


@pytest.fixture
def reset_handler() -> AsyncMock:
    mock = AsyncMock(spec=ResetPasswordHandlerProtocol)
    mock.handle.return_value = ResetPasswordResult()
    return mock


@pytest.fixture
def app(settings: Settings, request_handler: AsyncMock, reset_handler: AsyncMock) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(auth_api.router)

    container = make_async_container(
        PasswordResetApiProvider(
            settings=settings,
            request_handler=request_handler,
            reset_handler=reset_handler,
        )
    )
    setup_dishka(container, app)
    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_forgot_password_returns_202_with_generic_message(
    client: httpx.AsyncClient,
    request_handler: AsyncMock,
) -> None:
    response = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "teacher@example.com"},
    )

    assert response.status_code == 202
    assert response.json() == {
        "message": "Om kontot kan återställas skickas en återställningslänk."
    }
    request_handler.handle.assert_awaited_once()


@pytest.mark.asyncio
async def test_reset_password_returns_200_with_success_message(
    client: httpx.AsyncClient,
    reset_handler: AsyncMock,
) -> None:
    response = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "valid-token", "new_password": "strong-password"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Lösenordet har återställts. Logga in med ditt nya lösenord."
    }
    reset_handler.handle.assert_awaited_once()


@pytest.mark.asyncio
async def test_reset_password_returns_400_for_invalid_token(
    client: httpx.AsyncClient,
    reset_handler: AsyncMock,
) -> None:
    reset_handler.handle.side_effect = DomainError(
        code=ErrorCode.INVALID_PASSWORD_RESET_TOKEN,
        message="Ogiltig återställningslänk",
    )

    response = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "bad-token", "new_password": "strong-password"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == ErrorCode.INVALID_PASSWORD_RESET_TOKEN.value


@pytest.mark.asyncio
async def test_reset_password_returns_400_for_expired_token(
    client: httpx.AsyncClient,
    reset_handler: AsyncMock,
) -> None:
    reset_handler.handle.side_effect = DomainError(
        code=ErrorCode.PASSWORD_RESET_TOKEN_EXPIRED,
        message="Återställningslänken har gått ut",
    )

    response = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "expired-token", "new_password": "strong-password"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == ErrorCode.PASSWORD_RESET_TOKEN_EXPIRED.value


@pytest.mark.asyncio
async def test_reset_password_returns_400_for_missing_token(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/reset-password",
        json={"new_password": "strong-password"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == ErrorCode.VALIDATION_ERROR.value


@pytest.mark.asyncio
async def test_reset_password_returns_400_for_missing_new_password(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "valid-token"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == ErrorCode.VALIDATION_ERROR.value


@pytest.mark.asyncio
async def test_reset_password_returns_400_for_handler_validation_error(
    client: httpx.AsyncClient,
    reset_handler: AsyncMock,
) -> None:
    reset_handler.handle.side_effect = DomainError(
        code=ErrorCode.VALIDATION_ERROR,
        message="Lösenordet måste vara minst 8 tecken.",
    )

    response = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "valid-token", "new_password": "short"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == ErrorCode.VALIDATION_ERROR.value
