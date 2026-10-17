"""Saved exam ordering is a profile preference, not browser-local state."""

from collections.abc import AsyncIterator
from datetime import timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.handlers.exam_workspace_saved_index import (
    ListExamWorkspaceDocumentsHandler,
)
from skriptoteket.application.identity.handlers.get_profile import GetProfileHandler
from skriptoteket.application.identity.handlers.update_exam_list_ordering import (
    UpdateExamListOrderingHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.exam_index import SavedExam
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    curated_app_tool_id,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_index import ExamIndexRepositoryProtocol
from skriptoteket.protocols.exam_workspace import ListExamWorkspaceDocumentsHandlerProtocol
from skriptoteket.protocols.identity import (
    GetProfileHandlerProtocol,
    ProfileRepositoryProtocol,
    UpdateExamListOrderingHandlerProtocol,
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
PATH = "/api/v1/profile/exam-list-ordering"


class ExamListOrderingProvider(Provider):
    def __init__(self, index: ExamIndexRepositoryProtocol) -> None:
        super().__init__()
        self._index = index

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
    def list_documents(
        self,
        profiles: ProfileRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> ListExamWorkspaceDocumentsHandlerProtocol:
        return ListExamWorkspaceDocumentsHandler(index=self._index, profiles=profiles, uow=uow)

    @provide(scope=Scope.REQUEST)
    def update_ordering(
        self,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        clock: ClockProtocol,
    ) -> UpdateExamListOrderingHandlerProtocol:
        return UpdateExamListOrderingHandler(uow=uow, users=users, profiles=profiles, clock=clock)

    @provide(scope=Scope.REQUEST)
    def get_profile(
        self,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
    ) -> GetProfileHandlerProtocol:
        return GetProfileHandler(uow=uow, users=users, profiles=profiles)


@pytest.fixture
def index() -> AsyncMock:
    return AsyncMock(spec=ExamIndexRepositoryProtocol)


@pytest.fixture
async def app(
    settings: Settings,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    index: AsyncMock,
) -> AsyncIterator[FastAPI]:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(profile_api.router)
    app.include_router(exam_api.router)
    container = make_async_container(
        ProfileContinuationApiProvider(
            settings=settings, clock=clock, users=users, profiles=profiles
        ),
        ExamListOrderingProvider(index),
    )
    setup_dishka(container, app)
    yield app
    await container.close()


@pytest.mark.asyncio
async def test_ordering_survives_a_fresh_client_and_does_not_replace_other_preferences(
    app: FastAPI,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    index: AsyncMock,
) -> None:
    actor = seed_huleedu_projection(users=users, profiles=profiles)
    older = SavedExam(
        owner_user_id=actor.id,
        lineage_id=uuid4(),
        course_key="SVESVE01",
        title="Indexed title",
        saved_at=clock.now() - timedelta(days=1),
        head_vault_file_id=uuid4(),
        name="Different file name.provdokument.zip",
        version=7,
    )
    newer = older.model_copy(
        update={
            "lineage_id": uuid4(),
            "course_key": None,
            "saved_at": clock.now(),
            "head_vault_file_id": uuid4(),
            "title": "Unassigned newer exam",
        }
    )
    index.list_for_owner.return_value = [older, newer]
    assert profiles.result is not None
    before = profiles.result
    headers = signed_huleedu_headers(private_key=private_key, clock=clock)
    for ordering in ("newest", "course"):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as writer:
            response = await writer.patch(PATH, headers=headers, json={"ordering": ordering})
        assert response.status_code == 200, response.text
        assert response.json()["profile"]["exam_list_ordering"] == ordering
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as reader:
            fetched = await reader.get("/api/v1/profile", headers=headers)
            listed = await reader.get(
                "/api/v1/apps/documents.conversion_hub/exam-workspace/documents", headers=headers
            )
        assert fetched.status_code == 200, fetched.text
        assert fetched.json()["profile"]["exam_list_ordering"] == ordering
        assert listed.status_code == 200, listed.text
        payload = listed.json()
        assert payload["ordering"] == ordering
        expected = [newer, older] if ordering == "newest" else [older, newer]
        assert [exam["lineage_id"] for exam in payload["documents"]] == [
            str(exam.lineage_id) for exam in expected
        ]
        summary = next(exam for exam in payload["documents"] if exam["title"] == "Indexed title")
        assert summary["course_key"] == "SVESVE01"
        assert summary["version"] == 7
        assert summary["vault_file_id"] == str(older.head_vault_file_id)
        assert summary["name"] == older.name
        assert summary["saved_at"] == older.saved_at.isoformat().replace("+00:00", "Z")
        assert profiles.result.exam_courses == before.exam_courses
        assert profiles.result.locale == before.locale
        assert profiles.result.display_name == before.display_name


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [{"ordering": "title"}, {"ordering": None}, {}])
async def test_invalid_ordering_does_not_mutate_saved_preference(
    app: FastAPI,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    payload: dict[str, object],
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles)
    before = profiles.result
    headers = signed_huleedu_headers(private_key=private_key, clock=clock)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.patch(PATH, headers=headers, json=payload)
    assert response.status_code == 422, response.text
    assert profiles.result == before


@pytest.mark.asyncio
async def test_unauthenticated_ordering_write_is_rejected(
    app: FastAPI, users: UserRepositoryStub, profiles: ProfileRepositoryStub
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles)
    before = profiles.result
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.patch(PATH, json={"ordering": "newest"})
    assert response.status_code == 401, response.text
    assert profiles.result == before
