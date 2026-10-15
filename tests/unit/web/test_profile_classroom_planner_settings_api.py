"""Classroom planner settings route tests for tutorial seen sections.

Purpose:
    Verify that `PATCH /api/v1/profile/classroom-planner-settings` accepts the
    full list of seen Klassrumskartan tutorial sections, rejects unknown
    section ids, and that the profile response exposes the stored list.

Relationships:
    - Exercises `skriptoteket.web.api.v1.profile` through FastAPI with the real
      settings and profile handlers over protocol stubs.
    - Reuses the HuleEdu app-continuation verifier fixtures for authentication.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI
from pydantic import ValidationError
from starlette_dishka import setup_dishka

from skriptoteket.application.identity.handlers.get_profile import GetProfileHandler
from skriptoteket.application.identity.handlers.update_classroom_planner_settings import (
    UpdateClassroomPlannerSettingsHandler,
)
from skriptoteket.config import Settings
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    GetProfileHandlerProtocol,
    ProfileRepositoryProtocol,
    UpdateClassroomPlannerSettingsHandlerProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.web.api.v1 import profile as profile_api
from skriptoteket.web.api.v1.profile import UpdateClassroomPlannerSettingsRequest
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

_SETTINGS_PATH = "/api/v1/profile/classroom-planner-settings"


class ProfileHandlersProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def update_classroom_planner_settings(
        self,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        clock: ClockProtocol,
    ) -> UpdateClassroomPlannerSettingsHandlerProtocol:
        return UpdateClassroomPlannerSettingsHandler(
            uow=uow,
            users=users,
            profiles=profiles,
            clock=clock,
        )

    @provide(scope=Scope.REQUEST)
    def get_profile(
        self,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
    ) -> GetProfileHandlerProtocol:
        return GetProfileHandler(uow=uow, users=users, profiles=profiles)


@pytest.fixture
def app(
    settings: Settings,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(profile_api.router)
    container = make_async_container(
        ProfileContinuationApiProvider(
            settings=settings,
            clock=clock,
            users=users,
            profiles=profiles,
        ),
        ProfileHandlersProvider(),
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
async def test_settings_patch_stores_seen_sections_and_profile_get_returns_them(
    client: httpx.AsyncClient,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles)
    headers = signed_huleedu_headers(private_key=private_key, clock=clock)

    patched = await client.patch(
        _SETTINGS_PATH,
        headers=headers,
        json={"tutorial_seen_sections": ["planner_rules", "planner_overview", "planner_rules"]},
    )
    fetched = await client.get("/api/v1/profile", headers=headers)

    assert patched.status_code == 200
    assert patched.json()["profile"]["classroom_planner_tutorial_seen_sections"] == [
        "planner_rules",
        "planner_overview",
    ]
    assert fetched.status_code == 200
    assert fetched.json()["profile"]["classroom_planner_tutorial_seen_sections"] == [
        "planner_rules",
        "planner_overview",
    ]


@pytest.mark.asyncio
async def test_profile_get_returns_null_seen_sections_for_untouched_profile(
    client: httpx.AsyncClient,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles)

    response = await client.get(
        "/api/v1/profile",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
    )

    assert response.status_code == 200
    assert response.json()["profile"]["classroom_planner_tutorial_seen_sections"] is None


@pytest.mark.asyncio
async def test_settings_patch_rejects_unknown_section_without_writing(
    client: httpx.AsyncClient,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles)
    before = profiles.result

    response = await client.patch(
        _SETTINGS_PATH,
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
        json={"tutorial_seen_sections": ["planner_overview", "planner_unknown"]},
    )

    assert response.status_code == 422
    assert profiles.result == before


def test_settings_request_accepts_seen_sections_alone() -> None:
    request = UpdateClassroomPlannerSettingsRequest(tutorial_seen_sections=["planner_seating"])

    assert request.tutorial_seen_sections == ["planner_seating"]
    assert request.smart_enabled is None


def test_settings_request_accepts_empty_seen_sections_as_a_provided_field() -> None:
    request = UpdateClassroomPlannerSettingsRequest(tutorial_seen_sections=[])

    assert request.tutorial_seen_sections == []


def test_settings_request_rejects_empty_payload() -> None:
    with pytest.raises(ValidationError, match="At least one classroom planner setting"):
        UpdateClassroomPlannerSettingsRequest()


@pytest.mark.parametrize(
    "sections",
    [["planner_unknown"], ["Planner_Overview"], ["planner_overview", ""]],
)
def test_settings_request_rejects_unknown_section_ids(sections: list[str]) -> None:
    with pytest.raises(ValidationError, match="Unknown classroom planner tutorial sections"):
        UpdateClassroomPlannerSettingsRequest(tutorial_seen_sections=sections)


def test_settings_request_deduplicates_seen_sections_in_first_seen_order() -> None:
    request = UpdateClassroomPlannerSettingsRequest(
        tutorial_seen_sections=[
            "planner_grouping",
            "planner_overview",
            "planner_grouping",
            "planner_seating",
            "planner_overview",
        ]
    )

    assert request.tutorial_seen_sections == [
        "planner_grouping",
        "planner_overview",
        "planner_seating",
    ]
