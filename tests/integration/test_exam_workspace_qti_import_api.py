"""HTTP/DI and real PostgreSQL QTI package import/save/reopen proof, not live-host proof."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from dishka import Provider, Scope, from_context, make_async_container
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.exam_workspace_exports import (
    build_native_examnet_qti_package,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    GetExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_qti_import import (
    ImportExamWorkspaceQtiDocumentHandler,
    ParseExamWorkspaceQtiPackageHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_package_reader import (  # noqa: E501
    ExamNetQtiPackageReader,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.id_generator import UUID4Generator
from skriptoteket.infrastructure.repositories.exam_answer_key_enrichment_jobs import (
    PostgreSQLExamAnswerKeyEnrichmentJobRepository,
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
    GetExamWorkspaceDocumentHandlerProtocol,
    ImportExamWorkspaceQtiDocumentHandlerProtocol,
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
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_gap_fill_item,
    make_single_choice_item,
)
from tests.unit.web.test_apps_exam_workspace_answer_key_suggestions_api import FakeRegistry

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]
_BASE = "/api/v1/apps/documents.conversion_hub/exam-workspace"


class QtiImportApiProvider(Provider):
    registry = from_context(provides=CuratedAppRegistryProtocol, scope=Scope.APP)
    importer = from_context(provides=ImportExamWorkspaceQtiDocumentHandlerProtocol, scope=Scope.APP)
    reader = from_context(provides=GetExamWorkspaceDocumentHandlerProtocol, scope=Scope.APP)
    verifier = from_context(provides=HuleEduInternalIdentityVerifierProtocol, scope=Scope.APP)
    resolver = from_context(provides=HuleEduAppProjectionResolverProtocol, scope=Scope.APP)
    clock = from_context(provides=ClockProtocol, scope=Scope.APP)
    auth_outcomes = from_context(provides=AuthOutcomeRecorderProtocol, scope=Scope.APP)


def _exported_package_bytes() -> bytes:
    """A real exported package: one choice question and one gap-fill question."""
    document = NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="QTI-avsetning",
        items=(
            make_single_choice_item(),
            make_gap_fill_item(sequence=2, item_id="item_002"),
        ),
        origin=NativeExamDocumentOrigin(kind="created"),
    )
    package, _report = build_native_examnet_qti_package(
        document, package_name="qti-avsetning", qti_writer=ExamNetQtiPackageWriter()
    )
    return package


async def test_signed_in_teacher_imports_a_package_reopens_it_and_strangers_are_refused(
    session_factory: async_sessionmaker[AsyncSession], tmp_path
) -> None:
    actor = await create_owner(session_factory)
    clock = FixedClock(datetime.now(UTC))
    ids = UUID4Generator()
    codec = ExamWorkspaceContainerCodec()
    settings = Settings.model_construct(
        VAULT_MAX_FILE_BYTES=5_000_000, VAULT_MAX_TOTAL_BYTES=50_000_000
    )
    storage = LocalVaultStorage(vault_root=tmp_path)
    package = _exported_package_bytes()
    async with session_factory() as session:
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
        importer = ImportExamWorkspaceQtiDocumentHandler(
            parse=ParseExamWorkspaceQtiPackageHandler(
                reader=ExamNetQtiPackageReader(), settings=settings, id_generator=ids
            ),
            store=store,
            codec=codec,
            id_generator=ids,
        )
        container = make_async_container(
            QtiImportApiProvider(),
            context={
                CuratedAppRegistryProtocol: FakeRegistry(),
                ImportExamWorkspaceQtiDocumentHandlerProtocol: importer,
                GetExamWorkspaceDocumentHandlerProtocol: reader,
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
                response = await client.post(
                    _BASE + "/import-qti",
                    files={"file": ("prov.zip", package, "application/octet-stream")},
                    data={"course_key": "SVESVE02"},
                )
                assert response.status_code == 401, response.text
                app.dependency_overrides[require_app_user_api] = lambda: actor

                response = await client.post(
                    _BASE + "/import-qti",
                    files={"file": ("anteckningar.txt", b"not a zip", "application/octet-stream")},
                    data={"course_key": "SVESVE02"},
                )
                assert response.status_code == 422, response.text
                assert "Välj en .zip-fil med ett QTI-paket." in response.text

                response = await client.post(
                    _BASE + "/import-qti",
                    files={"file": ("prov.zip", package, "application/octet-stream")},
                    data={"course_key": "SVESVE02"},
                )
                assert response.status_code == 201, response.text
                summary = response.json()
                assert summary["version"] == 1
                assert summary["name"] == "prov.provdokument.zip"
                assert summary["title"] == "prov"
                assert summary["course_key"] == "SVESVE02"

                response = await client.get(_BASE + "/documents/" + summary["lineage_id"])
                assert response.status_code == 200, response.text
                opened = response.json()
                assert opened["document"]["origin"]["kind"] == "qti_import"
                assert opened["document"]["header"]["course"]["key"] == "SVESVE02"
                assert len(opened["document"]["items"]) == 2
                assert opened["document"]["items"][0]["kind"] == "single_choice"
                assert opened["document"]["items"][1]["kind"] == "gap_fill"
                assert opened["notes"] == []
        finally:
            await container.close()
