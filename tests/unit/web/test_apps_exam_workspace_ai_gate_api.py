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
      lease, so a handler that records no call proves no job, no call and no
      lease draw.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from uuid import UUID, uuid4

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from dishka import make_async_container
from fastapi import FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    curated_app_tool_id,
)
from skriptoteket.domain.identity.models import Role
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
from tests.unit.web.exam_workspace_ai_gate_test_support import (
    ExamWorkspaceAiGateProvider,
    HandlerDoubles,
    RecordingDouble,
    build_handler_doubles,
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
    return build_handler_doubles(sample_item=_SAMPLE_ITEM)


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


def _handler_for(handlers: HandlerDoubles, route: str) -> RecordingDouble:
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
    assert _handler_for(handlers, route).calls == []


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
    assert len(_handler_for(handlers, route).calls) == 1


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
    assert len(handlers.digiexam_import.calls) == 1


_WORD_LANE_UPLOADS = (
    ("prov.docx", b"docx-bytes"),
    ("prov.pdf", b"%PDF-1.4 fake"),
)


@pytest.mark.asyncio
@pytest.mark.parametrize("filename,content", _WORD_LANE_UPLOADS)
@pytest.mark.parametrize("role", [Role.USER, Role.CONTRIBUTOR])
async def test_word_lane_import_rejects_non_admin_roles_for_docx_and_pdf(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    handlers: HandlerDoubles,
    filename: str,
    content: bytes,
    role: Role,
    now: datetime,
) -> None:
    """A PDF upload keeps the Word import's AI access rule: non-admins get 403."""

    seed_huleedu_projection(users=users, profiles=profiles, role=role, now=now)

    response = await client.post(
        f"{_BASE}/documents",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
        files={"file": (filename, content, "application/octet-stream")},
    )

    assert response.status_code == 403
    details = response.json()["error"]["details"]
    assert set(details["required_roles"]) == {"admin", "superuser"}
    assert details["actual_role"] == role.value
    assert handlers.docx_import.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("filename,content", _WORD_LANE_UPLOADS)
async def test_word_lane_import_requires_sign_in_for_docx_and_pdf(
    client: httpx.AsyncClient,
    handlers: HandlerDoubles,
    filename: str,
    content: bytes,
) -> None:
    """A guest with no session gets exactly the same outcome for PDF as for DOCX."""

    response = await client.post(
        f"{_BASE}/documents",
        files={"file": (filename, content, "application/octet-stream")},
    )

    assert response.status_code == 401
    assert handlers.docx_import.calls == []
