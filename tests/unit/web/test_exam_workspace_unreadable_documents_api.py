"""The unreadable-documents route mirrors the saved list's access gate and shape."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceUnreadableDocument,
    ExamWorkspaceUnreadableDocumentListResponse,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_saved_index import (
    ListExamWorkspaceDocumentsHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    curated_app_tool_id,
)
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_index import ExamIndexRepositoryProtocol
from skriptoteket.protocols.exam_workspace import (
    ListExamWorkspaceDocumentsHandlerProtocol,
    ListUnreadableExamWorkspaceDocumentsHandlerProtocol,
)
from skriptoteket.protocols.identity import ProfileRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
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

_LIST_PATH = "/api/v1/apps/documents.conversion_hub/exam-workspace/documents"
_UNREADABLE_PATH = "/api/v1/apps/documents.conversion_hub/exam-workspace/unreadable-documents"
_NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)


class _StubUnreadableHandler:
    def __init__(self, response: ExamWorkspaceUnreadableDocumentListResponse) -> None:
        self._response = response

    async def handle(self, *, actor: User) -> ExamWorkspaceUnreadableDocumentListResponse:
        return self._response


class UnreadableDocumentsProvider(Provider):
    def __init__(
        self,
        index: ExamIndexRepositoryProtocol,
        response: ExamWorkspaceUnreadableDocumentListResponse,
        min_role: Role,
    ) -> None:
        super().__init__()
        self._index = index
        self._response = response
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
    def list_documents(
        self,
        profiles: ProfileRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> ListExamWorkspaceDocumentsHandlerProtocol:
        return ListExamWorkspaceDocumentsHandler(index=self._index, profiles=profiles, uow=uow)

    @provide(scope=Scope.REQUEST)
    def list_unreadable(
        self,
    ) -> ListUnreadableExamWorkspaceDocumentsHandlerProtocol:
        return _StubUnreadableHandler(self._response)


@pytest.fixture
def index() -> AsyncMock:
    return AsyncMock(spec=ExamIndexRepositoryProtocol)


@pytest.fixture
def unreadable_response() -> ExamWorkspaceUnreadableDocumentListResponse:
    return ExamWorkspaceUnreadableDocumentListResponse(
        documents=(
            ExamWorkspaceUnreadableDocument(
                lineage_id=uuid4(),
                vault_file_id=uuid4(),
                name="Old format.provdokument.zip",
                title="Old format",
                saved_at=_NOW,
            ),
        )
    )


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
    index: AsyncMock,
    unreadable_response: ExamWorkspaceUnreadableDocumentListResponse,
    min_role: Role,
) -> AsyncIterator[FastAPI]:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(exam_api.router)
    index.list_for_owner.return_value = []
    container = make_async_container(
        ProfileContinuationApiProvider(
            settings=settings, clock=clock, users=users, profiles=profiles
        ),
        UnreadableDocumentsProvider(index, unreadable_response, min_role),
    )
    setup_dishka(container, app)
    yield app
    await container.close()


@pytest.mark.asyncio
async def test_unreadable_documents_returns_exact_shape_for_allowed_user(
    app: FastAPI,
    clock: ClockStub,
    private_key: rsa.RSAPrivateKey,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    unreadable_response: ExamWorkspaceUnreadableDocumentListResponse,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles)
    headers = signed_huleedu_headers(private_key=private_key, clock=clock)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(_UNREADABLE_PATH, headers=headers)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert set(payload) == {"documents"}
    assert len(payload["documents"]) == 1
    (document,) = payload["documents"]
    expected = unreadable_response.documents[0]
    assert set(document) == {"lineage_id", "vault_file_id", "name", "title", "saved_at"}
    assert document["lineage_id"] == str(expected.lineage_id)
    assert document["vault_file_id"] == str(expected.vault_file_id)
    assert document["name"] == expected.name
    assert document["title"] == expected.title
    assert document["saved_at"] == expected.saved_at.isoformat().replace("+00:00", "Z")


@pytest.mark.asyncio
@pytest.mark.parametrize("min_role", [Role.ADMIN], indirect=True)
async def test_unreadable_documents_refuses_like_saved_list_without_access(
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
        listed = await client.get(_LIST_PATH, headers=headers)
        unreadable = await client.get(_UNREADABLE_PATH, headers=headers)

    assert listed.status_code == 403, listed.text
    assert unreadable.status_code == 403, unreadable.text
