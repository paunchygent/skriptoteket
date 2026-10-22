"""HTTP/DI and real PostgreSQL blank exam creation, listing and reopen proof."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import httpx
import pytest
from dishka import Provider, Scope, from_context, make_async_container
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.handlers.exam_workspace_blank_document import (
    CreateBlankExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    GetExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_saved_index import (
    ListExamWorkspaceDocumentsHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import UserProfile
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.id_generator import UUID4Generator
from skriptoteket.infrastructure.repositories.exam_answer_key_enrichment_jobs import (
    PostgreSQLExamAnswerKeyEnrichmentJobRepository,
)
from skriptoteket.infrastructure.repositories.exam_index_repository import (
    PostgreSQLExamIndexRepository,
)
from skriptoteket.infrastructure.repositories.profile_repository import (
    PostgreSQLProfileRepository,
)
from skriptoteket.infrastructure.repositories.user_vault_file_repository import (
    PostgreSQLUserVaultFileRepository,
)
from skriptoteket.infrastructure.security.huleedu_internal_identity import (
    HuleEduInternalIdentityVerifier,
)
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from skriptoteket.observability.auth_outcomes import PrometheusAuthOutcomeRecorder
from skriptoteket.protocols.auth_outcomes import AuthOutcomeRecorderProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace import (
    CreateBlankExamWorkspaceDocumentHandlerProtocol,
    GetExamWorkspaceDocumentHandlerProtocol,
    ListExamWorkspaceDocumentsHandlerProtocol,
)
from skriptoteket.protocols.identity import (
    HuleEduAppProjectionResolverProtocol,
    HuleEduInternalIdentityVerifierProtocol,
)
from skriptoteket.web.api.v1 import apps_conversion_hub_exam_workspace as documents_api
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.payload_guard_fixtures import unpooled_payload_guard_engine
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.exam_workspace_docx_background_support import document_store
from tests.integration.infrastructure.repositories.exam_workspace_test_support import create_owner
from tests.unit.web.test_apps_exam_workspace_answer_key_suggestions_api import FakeRegistry

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]
_BASE = "/api/v1/apps/documents.conversion_hub/exam-workspace"


class BlankApiProvider(Provider):
    registry = from_context(provides=CuratedAppRegistryProtocol, scope=Scope.APP)
    blank = from_context(provides=CreateBlankExamWorkspaceDocumentHandlerProtocol, scope=Scope.APP)
    reader = from_context(provides=GetExamWorkspaceDocumentHandlerProtocol, scope=Scope.APP)
    lister = from_context(provides=ListExamWorkspaceDocumentsHandlerProtocol, scope=Scope.APP)
    verifier = from_context(provides=HuleEduInternalIdentityVerifierProtocol, scope=Scope.APP)
    resolver = from_context(provides=HuleEduAppProjectionResolverProtocol, scope=Scope.APP)
    clock = from_context(provides=ClockProtocol, scope=Scope.APP)
    auth_outcomes = from_context(provides=AuthOutcomeRecorderProtocol, scope=Scope.APP)


async def test_signed_in_teacher_creates_lists_and_reopens_a_blank_exam(
    session_factory: async_sessionmaker[AsyncSession], tmp_path
) -> None:
    actor = await create_owner(session_factory)
    now = datetime.now(UTC)
    clock = FixedClock(now)
    ids = UUID4Generator()
    codec = ExamWorkspaceContainerCodec()
    settings = Settings.model_construct(
        VAULT_MAX_FILE_BYTES=5_000_000, VAULT_MAX_TOTAL_BYTES=50_000_000
    )
    storage = LocalVaultStorage(vault_root=tmp_path)
    async with session_factory() as session:
        await PostgreSQLProfileRepository(session).create(
            profile=UserProfile(user_id=actor.id, created_at=now, updated_at=now)
        )
        jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)
        uow = SQLAlchemyUnitOfWork(session)
        vault = PostgreSQLUserVaultFileRepository(
            session, unpooled_payload_guard_engine(session.bind)
        )
        store = document_store(session, storage=storage, clock=clock, settings=settings, uow=uow)
        reader = GetExamWorkspaceDocumentHandler(
            vault_files=vault,
            codec=codec,
            store=store,
            jobs=jobs,
            uow=uow,
        )
        blank = CreateBlankExamWorkspaceDocumentHandler(
            store=store,
            codec=codec,
            id_generator=ids,
        )
        lister = ListExamWorkspaceDocumentsHandler(
            index=PostgreSQLExamIndexRepository(session),
            profiles=PostgreSQLProfileRepository(session),
            uow=uow,
        )
        container = make_async_container(
            BlankApiProvider(),
            context={
                CuratedAppRegistryProtocol: FakeRegistry(),
                CreateBlankExamWorkspaceDocumentHandlerProtocol: blank,
                GetExamWorkspaceDocumentHandlerProtocol: reader,
                ListExamWorkspaceDocumentsHandlerProtocol: lister,
                HuleEduInternalIdentityVerifierProtocol: HuleEduInternalIdentityVerifier(settings),
                HuleEduAppProjectionResolverProtocol: AsyncMock(),
                ClockProtocol: clock,
                AuthOutcomeRecorderProtocol: PrometheusAuthOutcomeRecorder(),
            },
        )
        app = FastAPI()
        app.middleware("http")(error_handler_middleware)
        app.include_router(documents_api.router)
        app.dependency_overrides[require_app_user_api] = lambda: actor
        setup_dishka(container, app)
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                # Without the signed-in teacher override the real identity gate refuses the request.
                app.dependency_overrides.pop(require_app_user_api)
                response = await client.post(_BASE + "/blank")
                assert response.status_code == 401, response.text
                app.dependency_overrides[require_app_user_api] = lambda: actor

                response = await client.post(_BASE + "/blank")
                assert response.status_code == 201, response.text
                summary = response.json()
                assert summary["version"] == 1
                assert summary["name"] == "Namnlöst prov.provdokument.zip"
                assert summary["title"] == ""
                assert summary["lineage_id"]

                response = await client.get(_BASE + "/documents")
                assert response.status_code == 200, response.text
                listed = response.json()
                assert len(listed["documents"]) == 1
                assert listed["documents"][0]["lineage_id"] == summary["lineage_id"]
                assert listed["documents"][0]["name"] == "Namnlöst prov.provdokument.zip"

                response = await client.get(_BASE + "/documents/" + summary["lineage_id"])
                assert response.status_code == 200, response.text
                opened = response.json()
                assert opened["document"]["title"] == ""
                assert opened["document"]["revision"] == 1
                assert len(opened["document"]["items"]) == 1
                assert opened["document"]["items"][0]["kind"] == "free_text"
        finally:
            await container.close()
