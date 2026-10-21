"""HTTP/DI and real PostgreSQL DigiExam import/save/reopen proof, not live-host proof."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from dishka import Provider, Scope, from_context, make_async_container
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.handlers.exam_workspace_digiexam_jobs import (
    ProcessExamWorkspaceDigiExamJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_imports import (
    ImportExamWorkspaceDigiExamDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    GetExamWorkspaceConversionStatusHandler,
    GetExamWorkspaceDocumentHandler,
    SaveExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_edit_lease import (
    ExamWorkspaceEditLeaseHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_undo_steps import (
    StoreExamWorkspaceUndoStepHandler,
)
from skriptoteket.config import Settings
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_image_readability import (
    PillowEmbeddedImageDecodability,
)
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
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository
from skriptoteket.infrastructure.repositories.user_vault_file_repository import (
    PostgreSQLUserVaultFileRepository,
)
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace import (
    GetExamWorkspaceConversionStatusHandlerProtocol,
    GetExamWorkspaceDocumentHandlerProtocol,
    ImportExamWorkspaceDigiExamDocumentHandlerProtocol,
    SaveExamWorkspaceDocumentHandlerProtocol,
)
from skriptoteket.protocols.exam_workspace_history import (
    StoreExamWorkspaceUndoStepHandlerProtocol,
)
from skriptoteket.web.api.v1 import apps_conversion_hub_exam_workspace as documents_api
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.exam_workspace_docx_background_support import document_store
from tests.integration.infrastructure.repositories.exam_workspace_test_support import create_owner
from tests.unit.web.test_apps_exam_workspace_answer_key_suggestions_api import FakeRegistry

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]
_BASE = "/api/v1/apps/documents.conversion_hub/exam-workspace"
_FIXTURES = Path("tests/fixtures/exam_conversion")


class DigiExamApiProvider(Provider):
    registry = from_context(provides=CuratedAppRegistryProtocol, scope=Scope.APP)
    importer = from_context(
        provides=ImportExamWorkspaceDigiExamDocumentHandlerProtocol, scope=Scope.APP
    )
    status = from_context(provides=GetExamWorkspaceConversionStatusHandlerProtocol, scope=Scope.APP)
    reader = from_context(provides=GetExamWorkspaceDocumentHandlerProtocol, scope=Scope.APP)
    writer = from_context(provides=SaveExamWorkspaceDocumentHandlerProtocol, scope=Scope.APP)
    steps = from_context(provides=StoreExamWorkspaceUndoStepHandlerProtocol, scope=Scope.APP)


@pytest.mark.parametrize(
    "filename,count",
    [
        ("1772718003-test-samma-prov-i-digiexam.dxe", 7),
        ("sanitized-embedded-image.dxe", 1),
    ],
)
async def test_real_dxe_upload_job_and_saved_edits_roundtrip_http_and_postgres(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path, filename: str, count: int
) -> None:
    actor = await create_owner(session_factory)
    clock = FixedClock(datetime.now(UTC))
    ids = UUID4Generator()
    codec = ExamWorkspaceContainerCodec()
    settings = Settings.model_construct(
        VAULT_MAX_FILE_BYTES=5_000_000, VAULT_MAX_TOTAL_BYTES=50_000_000
    )
    storage = LocalVaultStorage(vault_root=tmp_path)
    async with session_factory() as session:
        jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)
        uow = SQLAlchemyUnitOfWork(session)
        vault = PostgreSQLUserVaultFileRepository(session)
        store = document_store(session, storage=storage, clock=clock, settings=settings, uow=uow)
        reader = GetExamWorkspaceDocumentHandler(
            vault_files=vault,
            codec=codec,
            store=store,
            jobs=jobs,
            uow=uow,
        )
        importer = ImportExamWorkspaceDigiExamDocumentHandler(
            jobs=jobs,
            uow=uow,
            clock=clock,
            settings=settings,
            id_generator=ids,
        )
        status = GetExamWorkspaceConversionStatusHandler(
            jobs=jobs,
            index=PostgreSQLExamIndexRepository(session),
        )
        container = make_async_container(
            DigiExamApiProvider(),
            context={
                CuratedAppRegistryProtocol: FakeRegistry(),
                ImportExamWorkspaceDigiExamDocumentHandlerProtocol: importer,
                GetExamWorkspaceConversionStatusHandlerProtocol: status,
                GetExamWorkspaceDocumentHandlerProtocol: reader,
                SaveExamWorkspaceDocumentHandlerProtocol: SaveExamWorkspaceDocumentHandler(
                    vault_files=vault,
                    codec=codec,
                    store=store,
                    id_generator=ids,
                    jobs=jobs,
                ),
                StoreExamWorkspaceUndoStepHandlerProtocol: StoreExamWorkspaceUndoStepHandler(
                    vault_files=vault,
                    codec=codec,
                    store=store,
                    jobs=jobs,
                    id_generator=ids,
                    clock=clock,
                ),
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
                for bad_name, content, course in [
                    ("prov.docx", b"source", "SVESVE02"),
                    (filename, b"", "SVESVE02"),
                    (filename, b"source", "UNKNOWN-COURSE"),
                ]:
                    response = await client.post(
                        _BASE + "/import-digiexam",
                        files={
                            "file": (bad_name, content, "application/octet-stream"),
                        },
                        data={"course_key": course},
                    )
                    assert response.status_code == 422, response.text
                response = await client.post(
                    _BASE + "/import-digiexam",
                    files={
                        "file": (
                            filename,
                            (_FIXTURES / filename).read_bytes(),
                            "application/octet-stream",
                        ),
                    },
                    data={"course_key": "SVESVE02"},
                )
                assert response.status_code == 202, response.text
                queued = response.json()
                assert queued["state"] == "queued"
                async with uow:
                    job = await jobs.claim_next(
                        worker_id="dxe-api-test", now=clock.now(), lease_ttl=timedelta(minutes=5)
                    )
                assert job is not None
                assert str(job.id) == queued["job_id"]
                assert job.source_kind.value == "digiexam_import"
                finished = await ProcessExamWorkspaceDigiExamJobHandler(
                    jobs=jobs,
                    store=store,
                    users=PostgreSQLUserRepository(session),
                    uow=uow,
                    clock=clock,
                    id_generator=ids,
                    codec=codec,
                    image_decodability=PillowEmbeddedImageDecodability(),
                ).handle(job=job)
                assert finished.status.value == "succeeded"
                response = await client.get(_BASE + "/conversion-jobs/" + queued["job_id"])
                assert response.status_code == 200, response.text
                assert response.json()["state"] == "succeeded"
                path = _BASE + "/documents/" + queued["lineage_id"]
                response = await client.get(path)
                assert response.status_code == 200, response.text
                opened = response.json()
                assert len(opened["document"]["items"]) == count
                assert opened["document"]["origin"]["kind"] == "digiexam_import"
                assert opened["document"]["header"]["course"]["key"] == "SVESVE02"
                document = opened["document"]
                document["revision"] = 2
                document["title"] = "Lärarens redigerade DigiExam-prov"
                history = await client.get(path + "/history")
                assert history.status_code == 200, history.text
                tab_id = uuid4()
                await ExamWorkspaceEditLeaseHandler(
                    vault_files=vault, store=store, clock=clock
                ).claim(actor=actor, lineage_id=UUID(queued["lineage_id"]), tab_id=tab_id)
                response = await client.post(
                    path + "/autosaves",
                    json={
                        "expected_cursor": history.json()["cursor"],
                        "document": document,
                        "tab_id": str(tab_id),
                    },
                )
                assert response.status_code == 200, response.text
                assert response.json()["document"]["title"] == document["title"]
                # A fresh session must observe committed revision 2, not a cached identity map.
                lineage_id = job.workspace_lineage_id
                assert lineage_id is not None
        finally:
            await container.close()
    async with session_factory() as session:
        reopened = await GetExamWorkspaceDocumentHandler(
            vault_files=PostgreSQLUserVaultFileRepository(session),
            codec=codec,
            store=document_store(session, storage=storage, clock=clock, settings=settings),
            jobs=PostgreSQLExamAnswerKeyEnrichmentJobRepository(session),
            uow=SQLAlchemyUnitOfWork(session),
        ).handle(actor=actor, lineage_id=lineage_id)
        assert reopened.document.revision == 2
        assert reopened.document.title == "Lärarens redigerade DigiExam-prov"
        assert reopened.saved_document == reopened.document
