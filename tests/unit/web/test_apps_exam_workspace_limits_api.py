"""Signed-in exam workspace limits route: the exam size cap from its backend owner.

Repair for review F4 (follow-up to R4): signed-in teachers read the exam size
limit through their own route instead of spending the guests' hourly budget or
receiving the guest-limit refusal. The value is the injected settings'
``VAULT_MAX_FILE_BYTES`` read at request time, so a test override of the
setting proves the value is owned by the backend, not a constant.
"""

from collections.abc import AsyncIterator
from unittest.mock import Mock

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.exam_workspace import ExamCourseCatalogResponse
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    curated_app_tool_id,
)
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace import GetExamCourseCatalogHandlerProtocol
from skriptoteket.web.api.v1 import apps_conversion_hub_exam_workspace as exam_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.profile_app_continuation_support import (
    ClockStub,
    ProfileContinuationApiProvider,
    ProfileRepositoryStub,
    UserRepositoryStub,
    seed_huleedu_projection,
    signed_huleedu_headers,
)

pytest_plugins = ("tests.fixtures.profile_app_continuation_api_app",)

_LIMITS_PATH = "/api/v1/apps/documents.conversion_hub/exam-workspace/limits"
_COURSES_PATH = "/api/v1/apps/documents.conversion_hub/exam-workspace/courses"


class _StubCourseCatalogHandler:
    async def handle(self, *, actor: User) -> ExamCourseCatalogResponse:
        return ExamCourseCatalogResponse(
            generated_at="2026-10-22T00:00:00Z",
            courses=(),
            registered_course_keys=(),
        )


class LimitsApiProvider(Provider):
    def __init__(self, min_role: Role) -> None:
        super().__init__()
        self._min_role = min_role

    @provide(scope=Scope.APP)
    def registry(self) -> CuratedAppRegistryProtocol:
        registry = Mock(spec=CuratedAppRegistryProtocol)
        registry.get_by_app_id.return_value = CuratedAppDefinition(
            app_id="documents.conversion_hub",
            tool_id=curated_app_tool_id(app_id="documents.conversion_hub"),
            app_version="app:test",
            title="Conversion Hub",
            min_role=self._min_role,
            placements=[CuratedAppPlacement(profession_slug="larare", category_slug="ovrigt")],
        )
        return registry

    @provide(scope=Scope.REQUEST)
    def course_catalog(self) -> GetExamCourseCatalogHandlerProtocol:
        return _StubCourseCatalogHandler()  # type: ignore[return-value]


@pytest.fixture
def min_role(request: pytest.FixtureRequest) -> Role:
    param = getattr(request, "param", Role.USER)
    assert isinstance(param, Role)
    return param


@pytest.fixture
async def app(
    settings: Settings,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    min_role: Role,
) -> AsyncIterator[FastAPI]:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(exam_api.router)
    container = make_async_container(
        ProfileContinuationApiProvider(
            settings=settings, clock=clock, users=users, profiles=profiles
        ),
        LimitsApiProvider(min_role),
    )
    setup_dishka(container, app)
    yield app
    await container.close()


@pytest.mark.asyncio
async def test_limits_return_the_configured_max_exam_bytes(
    app: FastAPI,
    settings: Settings,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles)
    headers = signed_huleedu_headers(private_key=private_key, clock=clock)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(_LIMITS_PATH, headers=headers)

    assert response.status_code == 200, response.text
    assert response.json() == {"max_exam_bytes": settings.VAULT_MAX_FILE_BYTES}


@pytest.mark.asyncio
async def test_limits_read_the_value_from_the_injected_settings(
    settings: Settings,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    private_key: rsa.RSAPrivateKey,
    min_role: Role,
) -> None:
    settings.VAULT_MAX_FILE_BYTES = 7_000_000
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(exam_api.router)
    container = make_async_container(
        ProfileContinuationApiProvider(
            settings=settings, clock=clock, users=users, profiles=profiles
        ),
        LimitsApiProvider(min_role),
    )
    setup_dishka(container, app)
    try:
        seed_huleedu_projection(users=users, profiles=profiles)
        headers = signed_huleedu_headers(private_key=private_key, clock=clock)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as configured:
            response = await configured.get(_LIMITS_PATH, headers=headers)
    finally:
        await container.close()

    assert response.status_code == 200, response.text
    assert response.json() == {"max_exam_bytes": 7_000_000}


@pytest.mark.asyncio
async def test_limits_refuse_an_unauthenticated_request_like_the_courses_route(
    app: FastAPI,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        limits = await client.get(_LIMITS_PATH)
        courses = await client.get(_COURSES_PATH)

    assert limits.status_code == 401, limits.text
    assert courses.status_code == 401, courses.text


@pytest.mark.asyncio
@pytest.mark.parametrize("min_role", [Role.ADMIN], indirect=True)
async def test_limits_refuse_like_the_courses_route_without_conversion_hub_access(
    app: FastAPI,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles)
    headers = signed_huleedu_headers(private_key=private_key, clock=clock)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        limits = await client.get(_LIMITS_PATH, headers=headers)
        courses = await client.get(_COURSES_PATH, headers=headers)

    assert limits.status_code == 403, limits.text
    assert courses.status_code == 403, courses.text
