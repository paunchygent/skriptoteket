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
    RegistrationValidationField,
    ValidateRegistrationResult,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.identity import (
    RegisterUserHandlerProtocol,
    ValidateRegistrationHandlerProtocol,
)
from skriptoteket.web.api.v1 import auth as auth_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware


class AuthApiProvider(Provider):
    def __init__(
        self,
        *,
        settings: Settings,
        register_handler: AsyncMock,
        validate_registration_handler: AsyncMock,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._register_handler = register_handler
        self._validate_registration_handler = validate_registration_handler

    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        return self._settings

    @provide(scope=Scope.REQUEST)
    def register_user_handler(self) -> RegisterUserHandlerProtocol:
        return cast(RegisterUserHandlerProtocol, self._register_handler)

    @provide(scope=Scope.REQUEST)
    def validate_registration_handler(self) -> ValidateRegistrationHandlerProtocol:
        return cast(ValidateRegistrationHandlerProtocol, self._validate_registration_handler)


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def register_handler() -> AsyncMock:
    return AsyncMock(spec=RegisterUserHandlerProtocol)


@pytest.fixture
def validate_registration_handler() -> AsyncMock:
    return AsyncMock(spec=ValidateRegistrationHandlerProtocol)


@pytest.fixture
def app(
    settings: Settings,
    register_handler: AsyncMock,
    validate_registration_handler: AsyncMock,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(auth_api.router)

    container = make_async_container(
        AuthApiProvider(
            settings=settings,
            register_handler=register_handler,
            validate_registration_handler=validate_registration_handler,
        ),
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
async def test_register_returns_503_when_email_send_fails(
    client: httpx.AsyncClient,
    register_handler: AsyncMock,
) -> None:
    register_handler.handle.side_effect = DomainError(
        code=ErrorCode.EMAIL_SEND_FAILED,
        message="Kunde inte skicka verifieringsmail. Försök igen.",
        details={"retryable": False, "attempts": 3},
    )

    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "teacher@example.com",
            "password": "password123",
            "first_name": "Ada",
            "last_name": "Lovelace",
        },
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == ErrorCode.EMAIL_SEND_FAILED.value
    assert payload["error"]["message"] == "Kunde inte skicka verifieringsmail. Försök igen."


@pytest.mark.asyncio
async def test_register_validate_returns_field_level_feedback(
    client: httpx.AsyncClient,
    validate_registration_handler: AsyncMock,
) -> None:
    validate_registration_handler.handle.return_value = ValidateRegistrationResult(
        email=RegistrationValidationField(
            status="invalid",
            message=(
                "Endast kommuner och enskilda huvudmän kan registrera sig just nu. "
                "Använd din tjänsteadress från kommunen eller huvudmannen."
            ),
        ),
        password=RegistrationValidationField(status="valid", message=None),
    )

    response = await client.post(
        "/api/v1/auth/register/validate",
        json={
            "email": "teacher@gmail.com",
            "password": "password123",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "email": {
            "status": "invalid",
            "message": (
                "Endast kommuner och enskilda huvudmän kan registrera sig just nu. "
                "Använd din tjänsteadress från kommunen eller huvudmannen."
            ),
        },
        "password": {
            "status": "valid",
            "message": None,
        },
    }
