"""HTTP-level paid-AI admin gate coverage for the exam-workspace routes.

Purpose:
    Prove (TASK-SKRIPT-REP-0044 L1, L2) that the four exam-workspace routes
    which can start a paid LLM call return 403 for a signed-in user and a
    contributor without ever reaching their handler, while admins and
    superusers stay admitted. DigiExam import makes no LLM call and must stay
    open for every signed-in user.

Relationships:
    - Exercises `apps_conversion_hub_exam_workspace` and
      `apps_conversion_hub_exam_workspace_enrichment` through the real FastAPI
      dependency graph with Dishka protocol stubs.
    - The handlers own job enqueue, synchronous conversion and the token
      lease, so a handler that is never awaited proves no job, no call and no
      lease draw.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from typing import cast
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJobStatus,
)
from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceAnswerKeySuggestionsResponse,
    ExamWorkspaceConversionStatus,
    ExamWorkspaceEnrichmentState,
    ExamWorkspaceItemRetryResponse,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_content_tags import (
    ContentSuggestionsResponse,
    RequestExamContentSuggestionsHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    curated_app_tool_id,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace import (
    ImportExamWorkspaceDigiExamDocumentHandlerProtocol,
    ImportExamWorkspaceDocumentHandlerProtocol,
    RequestExamWorkspaceAnswerKeySuggestionsHandlerProtocol,
    RetryExamWorkspaceItemHandlerProtocol,
)
from skriptoteket.web.api.v1 import apps_conversion_hub_exam_workspace as exam_workspace_api
from skriptoteket.web.api.v1 import (
    apps_conversion_hub_exam_workspace_enrichment as enrichment_api,
)
from skriptoteket.web.api.v1.apps_conversion_hub_access import APP_ID
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.profile_app_continuation_support import (
    ClockStub,
    ProfileContinuationApiProvider,
    ProfileRepositoryStub,
    UserRepositoryStub,
    seed_huleedu_projection,
    signed_huleedu_headers,
)

pytestmark = pytest.mark.unit

_BASE = f"/api/v1/apps/{APP_ID}/exam-workspace"

GATED_ROUTES = (
    "content_suggestions",
    "docx_import",
    "retry_item",
    "answer_key_suggestions",
)

_EXPECTED_STATUS = {
    "content_suggestions": 202,
    "docx_import": 202,
    "retry_item": 200,
    "answer_key_suggestions": 200,
}


def _item_payload() -> dict[str, object]:
    """One valid single choice question."""

    return {
        "item_id": "item_001",
        "sequence": 1,
        "kind": "single_choice",
        "body": [
            {
                "heading_level": None,
                "segments": [{"kind": "text", "text": "Fråga?", "marks": []}],
            }
        ],
        "choices": [
            {
                "choice_id": "choice_001",
                "body": [
                    {
                        "heading_level": None,
                        "segments": [{"kind": "text", "text": "Ett", "marks": []}],
                    }
                ],
            },
            {
                "choice_id": "choice_002",
                "body": [
                    {
                        "heading_level": None,
                        "segments": [{"kind": "text", "text": "Två", "marks": []}],
                    }
                ],
            },
        ],
        "answer_key": {"origin": "absent"},
        "review": {"state": "review_complete", "parse_origin": "teacher_created"},
    }


def _document_payload(lineage_id: UUID) -> dict[str, object]:
    """One valid native exam document holding a single choice question."""

    return {
        "document_id": str(lineage_id),
        "revision": 1,
        "title": "Prov",
        "origin": {"kind": "created"},
        "items": [_item_payload()],
    }


_SAMPLE_ITEM = NativeExamItem.model_validate(_item_payload())


class ConversionHubRegistryStub:
    """A registry double granting access to the Conversion Hub curated app."""

    def __init__(self) -> None:
        self._app = CuratedAppDefinition(
            app_id=APP_ID,
            tool_id=curated_app_tool_id(app_id=APP_ID),
            app_version="app:test",
            title="Conversion Hub",
            min_role=Role.USER,
            placements=[CuratedAppPlacement(profession_slug="larare", category_slug="ovrigt")],
        )

    def list_all(self) -> list[CuratedAppDefinition]:
        return [self._app]

    def get_by_app_id(self, *, app_id: str) -> CuratedAppDefinition | None:
        return self._app if app_id == APP_ID else None

    def get_by_tool_id(self, *, tool_id: UUID) -> CuratedAppDefinition | None:
        del tool_id
        return None


@dataclass(frozen=True)
class HandlerDoubles:
    """The five route handlers the gated and DigiExam routes receive."""

    content_suggestions: AsyncMock
    docx_import: AsyncMock
    digiexam_import: AsyncMock
    retry_item: AsyncMock
    answer_key_suggestions: AsyncMock


class ExamWorkspaceAiGateProvider(Provider):
    def __init__(
        self,
        *,
        registry: CuratedAppRegistryProtocol,
        handlers: HandlerDoubles,
    ) -> None:
        super().__init__()
        self._registry = registry
        self._handlers = handlers

    @provide(scope=Scope.REQUEST)
    def registry(self) -> CuratedAppRegistryProtocol:
        return self._registry

    @provide(scope=Scope.REQUEST)
    def request_exam_content_suggestions_handler(self) -> RequestExamContentSuggestionsHandler:
        return cast(RequestExamContentSuggestionsHandler, self._handlers.content_suggestions)

    @provide(scope=Scope.REQUEST)
    def import_exam_workspace_document_handler(
        self,
    ) -> ImportExamWorkspaceDocumentHandlerProtocol:
        return cast(ImportExamWorkspaceDocumentHandlerProtocol, self._handlers.docx_import)

    @provide(scope=Scope.REQUEST)
    def import_exam_workspace_digiexam_document_handler(
        self,
    ) -> ImportExamWorkspaceDigiExamDocumentHandlerProtocol:
        return cast(
            ImportExamWorkspaceDigiExamDocumentHandlerProtocol, self._handlers.digiexam_import
        )

    @provide(scope=Scope.REQUEST)
    def retry_exam_workspace_item_handler(self) -> RetryExamWorkspaceItemHandlerProtocol:
        return cast(RetryExamWorkspaceItemHandlerProtocol, self._handlers.retry_item)

    @provide(scope=Scope.REQUEST)
    def request_exam_workspace_answer_key_suggestions_handler(
        self,
    ) -> RequestExamWorkspaceAnswerKeySuggestionsHandlerProtocol:
        return cast(
            RequestExamWorkspaceAnswerKeySuggestionsHandlerProtocol,
            self._handlers.answer_key_suggestions,
        )


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
def clock(now: datetime) -> ClockStub:
    return ClockStub(now=now)


@pytest.fixture
def users() -> UserRepositoryStub:
    return UserRepositoryStub()


@pytest.fixture
def profiles() -> ProfileRepositoryStub:
    return ProfileRepositoryStub()


@pytest.fixture
def handlers() -> HandlerDoubles:
    lineage_id = uuid4()
    content_suggestions = AsyncMock(spec=RequestExamContentSuggestionsHandler)
    content_suggestions.handle.return_value = ContentSuggestionsResponse(
        job_id=uuid4(),
        lineage_id=lineage_id,
        document_revision=1,
        course_key="MATMAT01a",
        state=ExamAnswerKeyEnrichmentJobStatus.QUEUED,
    )
    docx_import = AsyncMock(spec=ImportExamWorkspaceDocumentHandlerProtocol)
    docx_import.handle.return_value = _conversion_status(lineage_id)
    digiexam_import = AsyncMock(spec=ImportExamWorkspaceDigiExamDocumentHandlerProtocol)
    digiexam_import.handle.return_value = _conversion_status(lineage_id)
    retry_item = AsyncMock(spec=RetryExamWorkspaceItemHandlerProtocol)
    retry_item.handle.return_value = ExamWorkspaceItemRetryResponse(
        lineage_id=lineage_id,
        item=_SAMPLE_ITEM,
    )
    answer_key_suggestions = AsyncMock(spec=RequestExamWorkspaceAnswerKeySuggestionsHandlerProtocol)
    answer_key_suggestions.handle.return_value = ExamWorkspaceAnswerKeySuggestionsResponse(
        job_id=uuid4(),
        lineage_id=lineage_id,
        state=ExamWorkspaceEnrichmentState.QUEUED,
    )
    return HandlerDoubles(
        content_suggestions=content_suggestions,
        docx_import=docx_import,
        digiexam_import=digiexam_import,
        retry_item=retry_item,
        answer_key_suggestions=answer_key_suggestions,
    )


def _conversion_status(lineage_id: UUID) -> ExamWorkspaceConversionStatus:
    return ExamWorkspaceConversionStatus(
        job_id=uuid4(),
        lineage_id=lineage_id,
        state="queued",
        error_message=None,
        document_revision=None,
        questions_total=0,
        questions_done=0,
        units=(),
        summary=None,
    )


@pytest.fixture
def app(
    settings: Settings,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    handlers: HandlerDoubles,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(exam_workspace_api.router)
    app.include_router(enrichment_api.router)

    container = make_async_container(
        ProfileContinuationApiProvider(
            settings=settings,
            clock=clock,
            users=users,
            profiles=profiles,
        ),
        ExamWorkspaceAiGateProvider(
            registry=ConversionHubRegistryStub(),
            handlers=handlers,
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


async def _send(
    *,
    client: httpx.AsyncClient,
    route: str,
    lineage_id: UUID,
    headers: dict[str, str],
) -> httpx.Response:
    if route == "content_suggestions":
        return await client.post(
            f"{_BASE}/documents/{lineage_id}/content-suggestions",
            headers=headers,
        )
    if route == "docx_import":
        return await client.post(
            f"{_BASE}/documents",
            headers=headers,
            files={"file": ("prov.docx", b"docx-bytes", "application/octet-stream")},
        )
    if route == "retry_item":
        return await client.post(
            f"{_BASE}/documents/{lineage_id}/items/retry",
            headers=headers,
            json={
                "document": _document_payload(lineage_id),
                "item_id": "item_001",
                "kind": "single_choice",
            },
        )
    if route == "answer_key_suggestions":
        return await client.post(
            f"{_BASE}/documents/{lineage_id}/answer-key-suggestions",
            headers=headers,
            json={"document": _document_payload(lineage_id), "item_id": "item_001"},
        )
    raise AssertionError(f"unknown gated route: {route}")


def _handler_for(handlers: HandlerDoubles, route: str) -> AsyncMock:
    return {
        "content_suggestions": handlers.content_suggestions,
        "docx_import": handlers.docx_import,
        "retry_item": handlers.retry_item,
        "answer_key_suggestions": handlers.answer_key_suggestions,
    }[route]


@pytest.mark.asyncio
@pytest.mark.parametrize("route", GATED_ROUTES)
@pytest.mark.parametrize("role", [Role.USER, Role.CONTRIBUTOR])
async def test_gated_routes_reject_non_admin_roles_without_reaching_the_handler(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    handlers: HandlerDoubles,
    route: str,
    role: Role,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=role, now=now)
    lineage_id = uuid4()

    response = await _send(
        client=client,
        route=route,
        lineage_id=lineage_id,
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
    )

    assert response.status_code == 403
    details = response.json()["error"]["details"]
    assert set(details["required_roles"]) == {"admin", "superuser"}
    assert details["actual_role"] == role.value
    _handler_for(handlers, route).handle.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("route", GATED_ROUTES)
@pytest.mark.parametrize("role", [Role.ADMIN, Role.SUPERUSER])
async def test_gated_routes_admit_admin_roles_and_reach_the_handler(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    handlers: HandlerDoubles,
    route: str,
    role: Role,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=role, now=now)
    lineage_id = uuid4()

    response = await _send(
        client=client,
        route=route,
        lineage_id=lineage_id,
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
    )

    assert response.status_code == _EXPECTED_STATUS[route]
    _handler_for(handlers, route).handle.assert_awaited_once()


@pytest.mark.asyncio
async def test_digiexam_import_stays_open_for_signed_in_users(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    handlers: HandlerDoubles,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=Role.USER, now=now)

    response = await client.post(
        f"{_BASE}/import-digiexam",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
        files={"file": ("prov.dxe", b"digiexam-bytes", "application/octet-stream")},
    )

    assert response.status_code == 202
    handlers.digiexam_import.handle.assert_awaited_once()
