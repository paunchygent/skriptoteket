"""Shared fixtures for profile app-continuation route tests.

Purpose:
    Provide the FastAPI/Dishka test app used by HuleEdu app-continuation route,
    context-validation, and dependency-guard tests.

Relationships:
    - Uses the real verifier and projection resolver with protocol stubs.
    - Keeps split test modules below the repo file-size budget.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from datetime import datetime, timezone

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from dishka import make_async_container
from fastapi import Depends, FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import User
from skriptoteket.web.api.v1 import profile as profile_api
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.middleware.correlation import CorrelationMiddleware
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.profile_app_continuation_support import (
    ClockStub,
    ProfileContinuationApiProvider,
    ProfileRepositoryStub,
    UserRepositoryStub,
)

InvalidHeadersBuilder = Callable[[rsa.RSAPrivateKey, int], dict[str, str]]


@pytest.fixture
def clock() -> ClockStub:
    return ClockStub(datetime(2026, 4, 11, 12, 0, 0, tzinfo=timezone.utc))


@pytest.fixture
def private_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def settings(private_key: rsa.RSAPrivateKey) -> Settings:
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    settings = Settings()
    settings.HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY = public_key.decode("utf-8")
    return settings


@pytest.fixture
def users() -> UserRepositoryStub:
    return UserRepositoryStub()


@pytest.fixture
def profiles() -> ProfileRepositoryStub:
    return ProfileRepositoryStub()


@pytest.fixture
def app(
    settings: Settings,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
) -> FastAPI:
    app = FastAPI()
    app.add_middleware(CorrelationMiddleware)
    app.middleware("http")(error_handler_middleware)
    app.include_router(profile_api.router)

    @app.get("/api/v1/pr-0253/protected-read")
    async def protected_read(user: User = Depends(require_app_user_api)) -> dict[str, str]:
        return {"user_id": str(user.id)}

    @app.post("/api/v1/pr-0253/protected-write")
    async def protected_write(user: User = Depends(require_app_user_api)) -> dict[str, str]:
        return {"user_id": str(user.id)}

    container = make_async_container(
        ProfileContinuationApiProvider(
            settings=settings,
            clock=clock,
            users=users,
            profiles=profiles,
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
