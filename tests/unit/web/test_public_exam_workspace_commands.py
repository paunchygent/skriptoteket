"""Stateless public guest command routes: admission, document commands, catalog.

These tests run the real FastAPI router and the real domain command functions,
with a fake database admission handler and the real deterministic misspellings
handler. Every structure command's result is compared against a direct call to
the same domain function the signed-in workspace uses.
"""

from __future__ import annotations

import random
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

import httpx
import pytest
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI
from pydantic import BaseModel
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.exam_workspace_misspellings import (
    ExamWorkspaceMisspellingsRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_courses import (
    exam_course_catalog_without_profile,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_misspellings import (
    GenerateExamWorkspaceMisspellingsHandler,
)
from skriptoteket.application.curated_apps.handlers.public_exam_workspace_commands import (
    PublicExamWorkspaceCommandHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace import (
    native_exam_parent_commands as commands,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_course_catalog import (
    load_exam_course_catalog,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_change_type import (
    change_item_type,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    CuratedAppPublicAccessProfile,
    CuratedAppPublicCapability,
    CuratedAppPublicRuntimeStatus,
    CuratedAppUiMode,
    curated_app_tool_id,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace import (
    GenerateExamWorkspaceMisspellingsHandlerProtocol,
)
from skriptoteket.protocols.public_request_limits import (
    AdmitPublicRequestHandlerProtocol,
    PublicRequestAdmission,
    PublicRequestBucket,
    PublicRequestRefusal,
)
from skriptoteket.web.api.v1 import public_apps_exam_workspace_commands as api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
    make_paragraph,
    make_single_choice_item,
)

_BASE = "/api/v1/public/apps/documents.conversion_hub/exam-converter/workspace"
_CLIENT_IP = "127.0.0.1"


class FakeAdmitHandler:
    """A database-limiter double that records every admission attempt."""

    def __init__(self) -> None:
        self.calls: list[tuple[PublicRequestBucket, str]] = []
        self.refusal: PublicRequestRefusal | None = None

    async def admit(self, *, bucket: PublicRequestBucket, client_ip: str) -> PublicRequestAdmission:
        self.calls.append((bucket, client_ip))
        if self.refusal is not None:
            return PublicRequestAdmission(admitted=False, refusal=self.refusal)
        return PublicRequestAdmission(admitted=True, refusal=None)


class RecordingCommandHandler(PublicExamWorkspaceCommandHandler):
    """The real handler plus a call log so refused requests prove no command ran."""

    def __init__(self, *, rng: random.Random) -> None:
        super().__init__(rng=rng)
        self.create_parent_calls = 0

    def create_parent(self, **kwargs: Any):
        self.create_parent_calls += 1
        return super().create_parent(**kwargs)


def make_registry(
    *, runtime_status: CuratedAppPublicRuntimeStatus = CuratedAppPublicRuntimeStatus.ACTIVE
) -> CuratedAppRegistryProtocol:
    app = CuratedAppDefinition(
        app_id="documents.conversion_hub",
        tool_id=curated_app_tool_id(app_id="documents.conversion_hub"),
        app_version="app:test",
        ui_mode=CuratedAppUiMode.BESPOKE_REQUIRED,
        title="Konvertera dokument",
        summary="Konvertera DigiExam-prov.",
        min_role=Role.USER,
        public_access_profile=CuratedAppPublicAccessProfile.AUTHENTICATED_ONLY,
        public_capabilities=[
            CuratedAppPublicCapability(
                scope="exam_converter",
                profile=CuratedAppPublicAccessProfile.PUBLIC_BROWSER_RUNTIME,
                runtime_status=runtime_status,
            )
        ],
        placements=[CuratedAppPlacement(profession_slug="larare", category_slug="ovrigt")],
    )

    class Registry:
        def list_all(self) -> list[CuratedAppDefinition]:
            return [app]

        def get_by_app_id(self, *, app_id: str) -> CuratedAppDefinition | None:
            return app if app_id == "documents.conversion_hub" else None

        def get_by_tool_id(self, *, tool_id: Any) -> CuratedAppDefinition | None:
            return app if tool_id == app.tool_id else None

    return Registry()


class GuestCommandProvider(Provider):
    def __init__(
        self,
        *,
        registry: CuratedAppRegistryProtocol,
        admit: AdmitPublicRequestHandlerProtocol,
        commands: PublicExamWorkspaceCommandHandler,
        settings: Settings,
    ) -> None:
        super().__init__()
        self._registry = registry
        self._admit = admit
        self._commands = commands
        self._settings = settings

    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        return self._settings

    @provide(scope=Scope.APP)
    def registry(self) -> CuratedAppRegistryProtocol:
        return self._registry

    @provide(scope=Scope.APP)
    def admit_handler(self) -> AdmitPublicRequestHandlerProtocol:
        return self._admit

    @provide(scope=Scope.APP)
    def public_command_handler(self) -> PublicExamWorkspaceCommandHandler:
        return self._commands

    @provide(scope=Scope.APP)
    def misspellings_handler(self) -> GenerateExamWorkspaceMisspellingsHandlerProtocol:
        return GenerateExamWorkspaceMisspellingsHandler()


def make_app(
    *,
    registry: CuratedAppRegistryProtocol,
    admit: AdmitPublicRequestHandlerProtocol,
    commands: PublicExamWorkspaceCommandHandler,
    settings: Settings | None = None,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(api.router)
    container = make_async_container(
        GuestCommandProvider(
            registry=registry,
            admit=admit,
            commands=commands,
            settings=settings if settings is not None else Settings(),
        )
    )
    setup_dishka(container, app)
    return app


@pytest.fixture
def admit() -> FakeAdmitHandler:
    return FakeAdmitHandler()


@pytest.fixture
def command_handler() -> RecordingCommandHandler:
    return RecordingCommandHandler(rng=random.Random(1))


@pytest.fixture
def registry() -> CuratedAppRegistryProtocol:
    return make_registry()


@pytest.fixture
def app(
    registry: CuratedAppRegistryProtocol,
    admit: FakeAdmitHandler,
    command_handler: RecordingCommandHandler,
) -> FastAPI:
    return make_app(registry=registry, admit=admit, commands=command_handler)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


def _parent(*, parent_id: str, place: int, item_ids: tuple[str, ...]) -> NativeExamParent:
    return NativeExamParent(
        parent_id=parent_id,
        place=place,
        instruction=(make_paragraph("Läs texten."),),
        item_ids=item_ids,
    )


def _parented_document() -> NativeExamDocument:
    """One standalone question and one parent with two children."""
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Omprov: grammatik",
        items=(
            make_free_text_item(sequence=1, item_id="item_001"),
            make_free_text_item(sequence=2, item_id="item_002"),
            make_free_text_item(sequence=3, item_id="item_003"),
        ),
        parents=(_parent(parent_id="parent_001", place=1, item_ids=("item_002", "item_003")),),
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def _single_child_document() -> NativeExamDocument:
    """One parent holding the exam's only question."""
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Omprov: grammatik",
        items=(make_free_text_item(sequence=1, item_id="item_001"),),
        parents=(_parent(parent_id="parent_001", place=0, item_ids=("item_001",)),),
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def _json_ready(value: Any) -> Any:
    """Turn pydantic models and their containers into JSON-compatible structures."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _json_ready(entry) for key, entry in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_ready(entry) for entry in value]
    return value


def _body(document: NativeExamDocument, **fields: Any) -> dict[str, Any]:
    return {"document": document.model_dump(mode="json"), **_json_ready(fields)}


def _response_document(response: httpx.Response) -> NativeExamDocument:
    return NativeExamDocument.model_validate(response.json()["document"])


async def test_blank_returns_a_valid_single_question_document(
    client: httpx.AsyncClient, admit: FakeAdmitHandler
) -> None:
    response = await client.post(f"{_BASE}/blank")

    assert response.status_code == 200
    document = _response_document(response)
    assert len(document.items) == 1
    item = document.items[0]
    assert item.item_id == "item_001"
    assert item.sequence == 1
    assert item.kind is NativeExamItemKind.FREE_TEXT
    assert item.points == 1
    assert document.title == ""
    assert document.revision == 1
    assert document.header.course is None
    assert response.json()["export_blockers"] == [
        {"item_id": None, "reason": "title_without_text"},
        {"item_id": "item_001", "reason": "empty_question_text"},
    ]
    assert admit.calls == [(PublicRequestBucket.GUEST_EDIT, _CLIENT_IP)]
    assert response.headers.get("set-cookie") is None


async def test_create_parent_matches_the_domain_function(
    client: httpx.AsyncClient, admit: FakeAdmitHandler
) -> None:
    document = _parented_document()
    expected = commands.create_parent(
        document,
        instruction=(make_paragraph("Del A"),),
        child=make_free_text_item(),
        position=1,
    )

    response = await client.post(
        f"{_BASE}/parents",
        json=_body(
            document,
            instruction=(make_paragraph("Del A"),),
            child=make_free_text_item(),
            position=1,
        ),
    )

    assert response.status_code == 200
    assert _response_document(response) == expected


async def test_add_child_matches_the_domain_function(client: httpx.AsyncClient) -> None:
    document = _parented_document()
    expected = commands.add_child(
        document, parent_id="parent_001", child=make_free_text_item(), position=0
    )

    response = await client.post(
        f"{_BASE}/parents/parent_001/children",
        json=_body(document, child=make_free_text_item(), position=0),
    )

    assert response.status_code == 200
    assert _response_document(response) == expected


async def test_delete_child_matches_the_domain_function(client: httpx.AsyncClient) -> None:
    document = _parented_document()
    expected = commands.delete_child(document, parent_id="parent_001", item_id="item_002")

    response = await client.post(
        f"{_BASE}/parents/parent_001/children/item_002/delete",
        json=_body(document),
    )

    assert response.status_code == 200
    assert response.json()["removed_parent_id"] is None
    assert _response_document(response) == expected


async def test_reorder_children_matches_the_domain_function(client: httpx.AsyncClient) -> None:
    document = _parented_document()
    expected = commands.reorder_children(
        document, parent_id="parent_001", item_ids=("item_003", "item_002")
    )

    response = await client.post(
        f"{_BASE}/parents/parent_001/children/order",
        json=_body(document, item_ids=("item_003", "item_002")),
    )

    assert response.status_code == 200
    assert _response_document(response) == expected


@pytest.mark.parametrize("mode", ["keep_questions", "with_questions"])
async def test_delete_parent_matches_the_domain_function(
    client: httpx.AsyncClient, mode: str
) -> None:
    document = _parented_document()
    delete = (
        commands.delete_parent_with_children if mode == "with_questions" else commands.delete_parent
    )
    expected = delete(document, parent_id="parent_001")

    response = await client.post(
        f"{_BASE}/parents/parent_001/delete",
        json=_body(document, mode=mode),
    )

    assert response.status_code == 200
    assert response.json()["removed_parent_id"] == "parent_001"
    assert _response_document(response) == expected


async def test_change_type_matches_the_domain_function(client: httpx.AsyncClient) -> None:
    document = _parented_document()
    expected = change_item_type(
        document,
        item_id="item_001",
        target_kind=NativeExamItemKind.SINGLE_CHOICE,
        rng=random.Random(1),
    )

    response = await client.post(
        f"{_BASE}/change-type",
        json=_body(document, item_id="item_001", target_kind="single_choice"),
    )

    assert response.status_code == 200
    assert response.json()["dropped_content"] == list(expected.dropped_content)
    assert _response_document(response) == expected.document


async def test_change_type_returns_dropped_content(client: httpx.AsyncClient) -> None:
    document = NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Omprov: grammatik",
        items=(make_single_choice_item(),),
        origin=NativeExamDocumentOrigin(kind="created"),
    )

    response = await client.post(
        f"{_BASE}/change-type",
        json=_body(document, item_id="item_001", target_kind="gap_fill"),
    )

    assert response.status_code == 200
    assert response.json()["dropped_content"] == ["choices", "correct_choice_ids"]


async def test_deleting_the_last_question_refuses(client: httpx.AsyncClient) -> None:
    document = _single_child_document()

    response = await client.post(
        f"{_BASE}/parents/parent_001/children/item_001/delete",
        json=_body(document),
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"]["reason"] == "exam_requires_question"


async def test_misspellings_match_the_signed_in_handler(client: httpx.AsyncClient) -> None:
    request = ExamWorkspaceMisspellingsRequest(
        accepted_values=("NF", "Nf"),
        other_gold_answers=("NF-variant",),
        document_text="Skriv namnet på staden.",
    )

    response = await client.post(
        f"{_BASE}/answer-misspellings",
        json=request.model_dump(mode="json"),
    )

    assert response.status_code == 200
    expected = GenerateExamWorkspaceMisspellingsHandler().handle(request=request)
    assert response.json()["automatic_values"] == list(expected.automatic_values)


async def test_courses_need_no_user_and_keep_the_default_order(
    client: httpx.AsyncClient, admit: FakeAdmitHandler
) -> None:
    response = await client.get(f"{_BASE}/courses")

    assert response.status_code == 200
    expected = exam_course_catalog_without_profile()
    assert response.json()["registered_course_keys"] == []
    assert response.json()["courses"] == [
        course.model_dump(mode="json") for course in expected.courses
    ]
    assert response.json()["generated_at"] == load_exam_course_catalog().generated_at
    assert admit.calls == [(PublicRequestBucket.GUEST_EDIT, _CLIENT_IP)]


async def test_unused_catalog_path_has_no_profile_lookup(
    client: httpx.AsyncClient,
) -> None:
    """The guest catalog is the committed snapshot in file order, with no user anywhere."""

    response = await client.get(f"{_BASE}/courses")

    catalog = load_exam_course_catalog()
    assert response.json()["courses"] == [
        course.model_dump(mode="json") for course in catalog.courses
    ]


@pytest.mark.parametrize(
    "refusal", [PublicRequestRefusal.CALLER_LIMIT, PublicRequestRefusal.POOL_LIMIT]
)
async def test_refused_admission_returns_429_and_never_runs_the_command(
    client: httpx.AsyncClient,
    admit: FakeAdmitHandler,
    command_handler: RecordingCommandHandler,
    refusal: PublicRequestRefusal,
) -> None:
    admit.refusal = refusal

    response = await client.post(
        f"{_BASE}/parents",
        json=_body(
            _parented_document(),
            instruction=(make_paragraph("Del A"),),
            child=make_free_text_item(),
            position=1,
        ),
    )

    assert response.status_code == 429
    assert response.json()["error"]["details"] == {
        "reason": refusal.value,
        "bucket": PublicRequestBucket.GUEST_EDIT.value,
    }
    assert command_handler.create_parent_calls == 0


async def test_unknown_extra_field_in_a_body_is_refused(client: httpx.AsyncClient) -> None:
    body = _body(
        _parented_document(),
        instruction=(make_paragraph("Del A"),),
        child=make_free_text_item(),
        position=1,
    )
    body["expected_cursor"] = "5f0e5e5e-0000-0000-0000-000000000000"

    response = await client.post(f"{_BASE}/parents", json=body)

    assert response.status_code == 422


async def test_oversized_body_is_rejected(admit: FakeAdmitHandler) -> None:
    app = make_app(
        registry=make_registry(),
        admit=admit,
        commands=RecordingCommandHandler(rng=random.Random(1)),
        settings=Settings(PUBLIC_GUEST_EXAM_MAX_REQUEST_BYTES=64),
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as limited:
        response = await limited.post(
            f"{_BASE}/parents",
            json=_body(
                _parented_document(),
                instruction=(make_paragraph("Del A"),),
                child=make_free_text_item(),
                position=1,
            ),
        )

    assert response.status_code == 413
    assert response.json()["error"]["details"]["reason"] == "payload_too_large"
