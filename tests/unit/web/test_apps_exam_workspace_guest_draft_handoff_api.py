"""Sign-in guest-draft handoff routes: idempotent exam creation over the posted draft.

In-memory HTTP proof through the real router, the real creation path
(``ExamWorkspaceDocumentStore.save``, the Spara som creation function) and the
real claim handler, with in-memory vault and ledger doubles. Concurrency-backed
claim semantics are proven against real Postgres in the repository's
integration test.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import datetime
from io import BytesIO
from uuid import UUID, uuid4

import httpx
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from fastapi import FastAPI
from PIL import Image
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.handlers.exam_workspace_guest_draft_handoff import (
    ImportGuestExamDraftHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_json import (
    native_exam_document_json_bytes,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.auth_outcomes import AuthOutcomeRecorderProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace_guest_drafts import (
    ImportGuestExamDraftHandlerProtocol,
)
from skriptoteket.protocols.identity import (
    HuleEduAppProjectionResolverProtocol,
    HuleEduInternalIdentityVerifierProtocol,
)
from skriptoteket.web.api.v1 import apps_conversion_hub_exam_workspace as documents_api
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.time_fixtures import FixedClock
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _NOW,
    _actor,
    _Env,
    _settings,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
)
from tests.unit.web.test_apps_exam_workspace_answer_key_suggestions_api import FakeRegistry

_PATH = "/api/v1/apps/documents.conversion_hub/exam-workspace/guest-drafts"

type MultipartFile = tuple[None, str] | tuple[str, bytes, str]
"""One httpx file part: the document JSON text or one named asset payload."""

type MultipartFiles = dict[str, MultipartFile]
"""The httpx ``files`` mapping a guest-draft handoff carries."""


class InMemoryGuestDraftHandoffRepository:
    """Ledger double with the real claim semantics minus database blocking."""

    def __init__(self) -> None:
        self.rows: dict[tuple[UUID, UUID], UUID] = {}

    async def claim(
        self, *, owner_user_id: UUID, draft_id: UUID, lineage_id: UUID, now: datetime
    ) -> bool:
        key = (owner_user_id, draft_id)
        if key in self.rows:
            return False
        self.rows[key] = lineage_id
        return True

    async def get_lineage(self, *, owner_user_id: UUID, draft_id: UUID) -> UUID | None:
        return self.rows.get((owner_user_id, draft_id))


class _RefusingVerifier:
    """The signed-context boundary without a signed context: every request is rejected."""

    def verify(self, *, headers: Mapping[str, object], now_ts: int):
        raise DomainError(code=ErrorCode.UNAUTHORIZED, message="Saknad inloggningskontext.")


class _UnreachedResolver:
    """Never reached while the verifier refuses; refuses for the same reason."""

    async def resolve(self, *, context: object, correlation_id: UUID | None = None):
        raise DomainError(code=ErrorCode.UNAUTHORIZED, message="Saknad inloggningskontext.")


class _AuthStubProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def verifier(self) -> HuleEduInternalIdentityVerifierProtocol:
        return _RefusingVerifier()

    @provide(scope=Scope.REQUEST)
    def resolver(self) -> HuleEduAppProjectionResolverProtocol:
        return _UnreachedResolver()

    @provide(scope=Scope.REQUEST)
    def auth_outcomes(self) -> AuthOutcomeRecorderProtocol:
        return AuthOutcomeRecorderStub()


class AuthOutcomeRecorderStub:
    def record_context_verification(
        self, *, outcome: str, reason: str, correlation_id: UUID | None
    ) -> None:
        return None

    def record_projection_outcome(self, **kwargs: object) -> None:
        return None

    def record_rbac_decision(self, **kwargs: object) -> None:
        return None


def _handoff_handler(
    env: _Env, handoffs: InMemoryGuestDraftHandoffRepository
) -> ImportGuestExamDraftHandler:
    return ImportGuestExamDraftHandler(
        handoffs=handoffs,
        reader=env.get_handler,
        codec=env.codec,
        store=env.store,
        clock=FixedClock(_NOW),
        id_generator=env.ids,
        index=env.index,
    )


def _app(env: _Env, actor: User, handoffs: InMemoryGuestDraftHandoffRepository) -> FastAPI:
    container = make_async_container(
        context={
            Settings: _settings(),
            CuratedAppRegistryProtocol: FakeRegistry(),
            ImportGuestExamDraftHandlerProtocol: _handoff_handler(env, handoffs),
        },
    )
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(documents_api.router)
    app.dependency_overrides[require_app_user_api] = lambda: actor
    setup_dishka(container, app)
    return app


def _unauthenticated_app(env: _Env, handoffs: InMemoryGuestDraftHandoffRepository) -> FastAPI:
    container = make_async_container(
        _AuthStubProvider(),
        context={
            Settings: _settings(),
            ClockProtocol: FixedClock(_NOW),
            CuratedAppRegistryProtocol: FakeRegistry(),
            ImportGuestExamDraftHandlerProtocol: _handoff_handler(env, handoffs),
        },
    )
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(documents_api.router)
    setup_dishka(container, app)
    return app


def _png() -> bytes:
    buffer = BytesIO()
    Image.new("RGBA", (8, 4), (25, 130, 60, 180)).save(buffer, format="PNG")
    return buffer.getvalue()


def _picture_document() -> tuple[NativeExamDocument, str, bytes]:
    payload = _png()
    digest = hashlib.sha256(payload).hexdigest()
    asset_id = f"asset_{digest[:16]}"
    item = make_free_text_item().model_copy(
        update={
            "body": (
                NativeParagraph(
                    heading_level=None,
                    segments=(
                        NativeTextSegment(text="Betrakta: ", marks=()),
                        NativeAssetSegment(asset_id=asset_id),
                    ),
                ),
            )
        }
    )
    document = NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Omprov: grammatik",
        items=(item,),
        assets=(
            NativeExamAsset(
                asset_id=asset_id,
                sha256=digest,
                media_type="image/png",
                byte_length=len(payload),
            ),
        ),
        origin=NativeExamDocumentOrigin(kind="created"),
    )
    return document, asset_id, payload


def _multipart(
    document: NativeExamDocument, assets: Mapping[str, bytes] | None = None
) -> MultipartFiles:
    text = native_exam_document_json_bytes(document).decode("utf-8")
    files: MultipartFiles = {"document": (None, text)}
    for asset_id, payload in (assets or {}).items():
        files[f"asset:{asset_id}"] = (f"{asset_id}.png", payload, "image/png")
    return files


async def _post_draft(
    client: httpx.AsyncClient,
    document: NativeExamDocument,
    *,
    draft_id: UUID,
    assets: Mapping[str, bytes] | None = None,
) -> httpx.Response:
    return await client.post(
        _PATH,
        data={"draft_id": str(draft_id)},
        files=_multipart(document, assets),
    )


async def test_first_post_creates_one_vault_file_and_returns_the_posted_content() -> None:
    env = _Env()
    actor = _actor()
    handoffs = InMemoryGuestDraftHandoffRepository()
    document, asset_id, payload = _picture_document()
    app = _app(env, actor, handoffs)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await _post_draft(
                client, document, draft_id=uuid4(), assets={asset_id: payload}
            )

        assert response.status_code == 200, response.text
        created = response.json()
        assert created["document"]["title"] == "Omprov: grammatik"
        assert created["document"]["revision"] == 1
        assert UUID(created["document"]["document_id"]) == UUID(created["summary"]["lineage_id"])
        assert created["summary"]["name"] == "Omprov: grammatik.provdokument.zip"
        assert created["summary"]["version"] == 1
        assert created["notes"] == []

        assert len(env.vault_files.files) == 1
        vault_file = next(iter(env.vault_files.files.values()))
        assert vault_file.name == "Omprov: grammatik.provdokument.zip"
        assert vault_file.document_lineage_id == UUID(created["summary"]["lineage_id"])
        container = env.codec.parse(
            content=await env.store.load(actor=actor, vault_file=vault_file)
        )
        assert container.document == NativeExamDocument.model_validate(created["saved_document"])
        assert container.assets_by_id == {asset_id: payload}
        assert container.notes == ()
    finally:
        await _close_app(app)


async def test_repeated_post_returns_the_first_exam_without_creating_anything() -> None:
    env = _Env()
    actor = _actor()
    handoffs = InMemoryGuestDraftHandoffRepository()
    document, asset_id, payload = _picture_document()
    draft_id = uuid4()
    app = _app(env, actor, handoffs)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            first = await _post_draft(
                client, document, draft_id=draft_id, assets={asset_id: payload}
            )
            assert first.status_code == 200, first.text
            created = first.json()
            lineage_id = UUID(created["summary"]["lineage_id"])

            # A repeated post may carry different content; the first exam still answers.
            repeated = await _post_draft(
                client,
                document.model_copy(update={"title": "Annat"}),
                draft_id=draft_id,
                assets={asset_id: payload},
            )

        assert repeated.status_code == 200, repeated.text
        again = repeated.json()
        assert UUID(again["summary"]["lineage_id"]) == lineage_id
        assert again["document"]["title"] == "Omprov: grammatik"
        assert again["document"] == created["document"]
        assert len(env.vault_files.files) == 1
        assert handoffs.rows[(actor.id, draft_id)] == lineage_id
    finally:
        await _close_app(app)


async def test_different_draft_id_creates_a_second_exam() -> None:
    env = _Env()
    actor = _actor()
    handoffs = InMemoryGuestDraftHandoffRepository()
    document, asset_id, payload = _picture_document()
    app = _app(env, actor, handoffs)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            first = await _post_draft(
                client, document, draft_id=uuid4(), assets={asset_id: payload}
            )
            second = await _post_draft(
                client, document, draft_id=uuid4(), assets={asset_id: payload}
            )

        assert first.status_code == 200, first.text
        assert second.status_code == 200, second.text
        assert UUID(first.json()["summary"]["lineage_id"]) != UUID(
            second.json()["summary"]["lineage_id"]
        )
        assert len(env.vault_files.files) == 2
    finally:
        await _close_app(app)


async def test_picture_part_mismatch_is_refused_and_creates_nothing() -> None:
    env = _Env()
    actor = _actor()
    handoffs = InMemoryGuestDraftHandoffRepository()
    document, asset_id, _payload = _picture_document()
    app = _app(env, actor, handoffs)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            refused = await _post_draft(
                client, document, draft_id=uuid4(), assets={asset_id: b"not the declared picture"}
            )

        assert refused.status_code == 422, refused.text
        assert refused.json()["error"]["details"]["reason"] == "asset_mismatch"
        assert env.vault_files.files == {}
        assert handoffs.rows == {}
    finally:
        await _close_app(app)


async def test_unauthenticated_post_is_rejected() -> None:
    env = _Env()
    handoffs = InMemoryGuestDraftHandoffRepository()
    document, asset_id, payload = _picture_document()
    app = _unauthenticated_app(env, handoffs)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await _post_draft(
                client, document, draft_id=uuid4(), assets={asset_id: payload}
            )

        assert response.status_code == 401, response.text
        assert env.vault_files.files == {}
        assert handoffs.rows == {}
    finally:
        await _close_app(app)


async def _close_app(app: FastAPI) -> None:
    container: AsyncContainer | None = getattr(app.state, "dishka_container", None)
    if container is not None:
        await container.close()
