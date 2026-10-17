"""Own-course PATCH/read contract through the real profile API and handlers."""

from collections.abc import AsyncIterator
from unittest.mock import Mock

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.handlers.exam_workspace_courses import (
    GetExamCourseCatalogHandler,
)
from skriptoteket.application.identity.handlers.get_profile import GetProfileHandler
from skriptoteket.application.identity.handlers.update_exam_courses import (
    UpdateExamCoursesHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.exam_course_catalog import (
    load_exam_course_catalog,
)
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    curated_app_tool_id,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace import GetExamCourseCatalogHandlerProtocol
from skriptoteket.protocols.identity import (
    GetProfileHandlerProtocol,
    ProfileRepositoryProtocol,
    UpdateExamCoursesHandlerProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.web.api.v1 import apps_conversion_hub_exam_workspace as exam_api
from skriptoteket.web.api.v1 import profile as profile_api
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

PATH = "/api/v1/profile/exam-courses"
# Deliberately reverse alphabetical order, and mix GY11, GY25 and a subject-band entry.
COURSE_KEYS = ["SVEN2000X", "SVESVE01", "GRGRMAT01/7-9"]


class ExamCoursesProvider(Provider):
    @provide(scope=Scope.APP)
    def registry(self) -> CuratedAppRegistryProtocol:
        registry = Mock(spec=CuratedAppRegistryProtocol)
        registry.get_by_app_id.return_value = CuratedAppDefinition(
            app_id="documents.conversion_hub",
            tool_id=curated_app_tool_id(app_id="documents.conversion_hub"),
            app_version="app:test",
            title="Conversion Hub",
            min_role=Role.USER,
            placements=[CuratedAppPlacement(profession_slug="larare", category_slug="ovrigt")],
        )
        return registry

    @provide(scope=Scope.REQUEST)
    def course_catalog(
        self,
        profiles: ProfileRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> GetExamCourseCatalogHandlerProtocol:
        return GetExamCourseCatalogHandler(profiles=profiles, uow=uow)

    @provide(scope=Scope.REQUEST)
    def update_exam_courses(
        self,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        clock: ClockProtocol,
    ) -> UpdateExamCoursesHandlerProtocol:
        return UpdateExamCoursesHandler(uow=uow, users=users, profiles=profiles, clock=clock)

    @provide(scope=Scope.REQUEST)
    def get_profile(
        self,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
    ) -> GetProfileHandlerProtocol:
        return GetProfileHandler(uow=uow, users=users, profiles=profiles)


@pytest.fixture
async def client(
    settings: Settings,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
) -> AsyncIterator[httpx.AsyncClient]:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(profile_api.router)
    app.include_router(exam_api.router)
    container = make_async_container(
        ProfileContinuationApiProvider(
            settings=settings, clock=clock, users=users, profiles=profiles
        ),
        ExamCoursesProvider(),
    )
    setup_dishka(container, app)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as session:
        yield session
    await container.close()


@pytest.mark.asyncio
async def test_patch_and_read_keep_catalog_key_order_and_clear_explicit_empty_list(
    client: httpx.AsyncClient,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles)
    headers = signed_huleedu_headers(private_key=private_key, clock=clock)
    preference = {"school_forms": ["grundskolan", "gymnasiet"], "course_keys": COURSE_KEYS}

    patched = await client.patch(PATH, headers=headers, json=preference)
    assert patched.status_code == 200, patched.text
    assert patched.json()["profile"]["exam_courses"] == preference
    fetched = await client.get("/api/v1/profile", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["profile"]["exam_courses"] == preference

    cleared = {"school_forms": ["gymnasiet"], "course_keys": []}
    response = await client.patch(PATH, headers=headers, json=cleared)
    assert response.status_code == 200, response.text
    fetched = await client.get("/api/v1/profile", headers=headers)
    assert fetched.json()["profile"]["exam_courses"] == cleared


@pytest.mark.asyncio
async def test_unknown_key_rejects_whole_update_with_named_field_error(
    client: httpx.AsyncClient,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles)
    headers = signed_huleedu_headers(private_key=private_key, clock=clock)
    valid = {"school_forms": ["gymnasiet"], "course_keys": COURSE_KEYS[:1]}
    saved = await client.patch(PATH, headers=headers, json=valid)
    assert saved.status_code == 200, saved.text
    before = profiles.result

    response = await client.patch(
        PATH,
        headers=headers,
        json={"school_forms": ["grundskolan"], "course_keys": [COURSE_KEYS[2], "missing:key"]},
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["details"]["field"] == "course_keys"
    assert profiles.result == before
    fetched = await client.get("/api/v1/profile", headers=headers)
    assert fetched.json()["profile"]["exam_courses"] == valid


@pytest.mark.asyncio
async def test_workspace_catalog_http_read_uses_saved_actor_preferences(
    client: httpx.AsyncClient,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles)
    headers = signed_huleedu_headers(private_key=private_key, clock=clock)
    saved = await client.patch(
        PATH,
        headers=headers,
        json={"school_forms": ["gymnasiet", "grundskolan"], "course_keys": COURSE_KEYS},
    )
    assert saved.status_code == 200, saved.text

    response = await client.get(
        "/api/v1/apps/documents.conversion_hub/exam-workspace/courses", headers=headers
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["registered_course_keys"] == COURSE_KEYS
    returned_keys = [course["key"] for course in payload["courses"]]
    assert returned_keys[: len(COURSE_KEYS)] == COURSE_KEYS
    assert returned_keys[len(COURSE_KEYS) :] == [
        course.key for course in load_exam_course_catalog().courses if course.key not in COURSE_KEYS
    ]
