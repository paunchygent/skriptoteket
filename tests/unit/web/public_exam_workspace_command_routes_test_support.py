"""Shared provider, fixture and builder machinery for the public command route tests.

The guest command suites share one admission double, one registry double and
one document builder set so each suite file stays under the 500-line boundary
without duplicating the wiring.

Test modules rebind the fixtures they need (``admit = route_support.admit``)
and define only their own ``app``/``client`` pair, since the command suites
mount the command router.
"""

from __future__ import annotations

import random
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import httpx
import pytest
from dishka import Provider, Scope, make_async_container, provide
from fastapi import APIRouter, FastAPI
from pydantic import BaseModel, JsonValue
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.handlers.exam_workspace_misspellings import (
    GenerateExamWorkspaceMisspellingsHandler,
)
from skriptoteket.application.curated_apps.handlers.public_exam_workspace_commands import (
    PublicExamWorkspaceCommandHandler,
)
from skriptoteket.application.curated_apps.public_exam_workspace import (
    PublicExamCreatedPartResponse,
    PublicExamDocumentCommandResponse,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
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
from skriptoteket.web.api.v1 import public_apps_exam_workspace_commands as commands_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
    make_paragraph,
)

_BASE = "/api/v1/public/apps/documents.conversion_hub/exam-converter/workspace"
_CLIENT_IP = "127.0.0.1"

type BodyField = (
    BaseModel | JsonValue | tuple[BodyField, ...] | list[BodyField] | dict[str, BodyField]
)
"""One JSON request field: a model, JSON value, or a nesting of them."""


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
        self.group_items_calls = 0
        self.create_empty_part_calls = 0
        self.move_item_calls = 0

    def create_parent(
        self,
        *,
        document: NativeExamDocument,
        instruction: tuple[NativeParagraph, ...],
        child: NativeExamItem,
        position: int,
    ) -> PublicExamDocumentCommandResponse:
        self.create_parent_calls += 1
        return super().create_parent(
            document=document, instruction=instruction, child=child, position=position
        )

    def group_items(
        self, *, document: NativeExamDocument, item_ids: tuple[str, ...]
    ) -> PublicExamCreatedPartResponse:
        self.group_items_calls += 1
        return super().group_items(document=document, item_ids=item_ids)

    def create_empty_part(
        self, *, document: NativeExamDocument, position: int
    ) -> PublicExamCreatedPartResponse:
        self.create_empty_part_calls += 1
        return super().create_empty_part(document=document, position=position)

    def move_item(
        self,
        *,
        document: NativeExamDocument,
        item_id: str,
        target_parent_id: str | None,
    ) -> PublicExamDocumentCommandResponse:
        self.move_item_calls += 1
        return super().move_item(
            document=document, item_id=item_id, target_parent_id=target_parent_id
        )


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

        def get_by_tool_id(self, *, tool_id: UUID) -> CuratedAppDefinition | None:
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


def mount_route_app(*, provider: Provider, router: APIRouter) -> FastAPI:
    """Assemble the FastAPI app for one public router and its Dishka provider."""
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(router)
    container = make_async_container(provider)
    setup_dishka(container, app)
    return app


def make_command_app(
    *,
    registry: CuratedAppRegistryProtocol,
    admit: AdmitPublicRequestHandlerProtocol,
    commands: PublicExamWorkspaceCommandHandler,
    settings: Settings | None = None,
) -> FastAPI:
    return mount_route_app(
        provider=GuestCommandProvider(
            registry=registry,
            admit=admit,
            commands=commands,
            settings=settings if settings is not None else Settings(),
        ),
        router=commands_api.router,
    )


@pytest.fixture
def admit() -> FakeAdmitHandler:
    return FakeAdmitHandler()


@pytest.fixture
def command_handler() -> RecordingCommandHandler:
    return RecordingCommandHandler(rng=random.Random(1))


@pytest.fixture
def registry() -> CuratedAppRegistryProtocol:
    return make_registry()


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


def _json_ready(value: BodyField) -> JsonValue:
    """Turn pydantic models and their containers into JSON-compatible structures."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _json_ready(entry) for key, entry in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_ready(entry) for entry in value]
    return value


def _body(document: NativeExamDocument, **fields: BodyField) -> dict[str, JsonValue]:
    body: dict[str, JsonValue] = {"document": document.model_dump(mode="json")}
    for key, field in fields.items():
        body[key] = _json_ready(field)
    return body


def _response_document(response: httpx.Response) -> NativeExamDocument:
    return NativeExamDocument.model_validate(response.json()["document"])


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
