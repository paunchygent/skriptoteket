"""HTTP/DI + real PostgreSQL proof; model answers are synthetic, not live API proof."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from dishka import Provider, Scope, from_context, make_async_container
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceAnswerKeySuggestionsResponse,
)
from skriptoteket.application.curated_apps.handlers.exam_answer_key_enrichment_attempts import (
    AnswerKeyAttemptLedger,
)
from skriptoteket.application.curated_apps.handlers.exam_answer_key_enrichment_workspace_lane import (  # noqa: E501
    ExamAnswerKeyEnrichmentWorkspaceLane,
)
from skriptoteket.application.curated_apps.handlers.exam_answer_key_provider_attempts import (
    AnswerKeyProviderAttemptRunner,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_digiexam_jobs import (
    ProcessExamWorkspaceDigiExamJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_imports import (
    ImportExamWorkspaceDigiExamDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_enrichment import (
    GetExamWorkspaceAnswerKeySuggestionsStatusHandler,
    RequestExamWorkspaceAnswerKeySuggestionsHandler,
    WorkspaceAnswerKeyRequestPayload,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.identity.models import Role
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_image_readability import (
    PillowEmbeddedImageDecodability,
)
from skriptoteket.infrastructure.llm.answer_key_provider_selection import (
    FixedRouteAnswerKeyProviderSelector,
)
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace import (
    GetExamWorkspaceAnswerKeySuggestionsStatusHandlerProtocol,
    ImportExamWorkspaceDigiExamDocumentHandlerProtocol,
    RequestExamWorkspaceAnswerKeySuggestionsHandlerProtocol,
)
from skriptoteket.web.api.v1 import apps_conversion_hub_exam_workspace as documents_api
from skriptoteket.web.api.v1 import apps_conversion_hub_exam_workspace_enrichment as suggestions_api
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.exam_workspace_conversion_support import SETTINGS, ConversionWorld, Ids
from tests.integration.infrastructure.repositories.exam_workspace_test_support import create_owner
from tests.unit.application.curated_apps.handlers.answer_key_enrichment_test_support import _route
from tests.unit.application.curated_apps.test_exam_workspace_digiexam_suggestions import FIXTURE
from tests.unit.web.test_apps_exam_workspace_answer_key_suggestions_api import FakeRegistry
from tests.unit.workers.test_exam_workspace_digiexam_suggestion_worker import (
    CapturingModel,
    assert_item_local_suggestions,
)

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]
_BASE = "/api/v1/apps/documents.conversion_hub/exam-workspace"


class SuggestionApiProvider(Provider):
    registry = from_context(provides=CuratedAppRegistryProtocol, scope=Scope.APP)
    importer = from_context(
        provides=ImportExamWorkspaceDigiExamDocumentHandlerProtocol, scope=Scope.APP
    )
    requester = from_context(
        provides=RequestExamWorkspaceAnswerKeySuggestionsHandlerProtocol, scope=Scope.APP
    )
    status = from_context(
        provides=GetExamWorkspaceAnswerKeySuggestionsStatusHandlerProtocol, scope=Scope.APP
    )


async def test_real_ak7_import_request_poll_and_review_with_http_di_and_postgres(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    actor = await create_owner(session_factory, role=Role.ADMIN)
    clock = FixedClock(datetime.now(UTC))
    storage = LocalVaultStorage(vault_root=tmp_path)
    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        importer = ImportExamWorkspaceDigiExamDocumentHandler(
            jobs=world.jobs, uow=world.uow, clock=clock, settings=SETTINGS, id_generator=Ids()
        )
        requester = RequestExamWorkspaceAnswerKeySuggestionsHandler(
            enrichment_jobs=world.jobs,
            suggestion_jobs=world.jobs,
            enrichment_enabled=True,
            vault_files=world.vault_files,
            uow=world.uow,
            clock=clock,
            id_generator=Ids(),
        )
        status = GetExamWorkspaceAnswerKeySuggestionsStatusHandler(enrichment_jobs=world.jobs)
        container = make_async_container(
            SuggestionApiProvider(),
            context={
                CuratedAppRegistryProtocol: FakeRegistry(),
                ImportExamWorkspaceDigiExamDocumentHandlerProtocol: importer,
                RequestExamWorkspaceAnswerKeySuggestionsHandlerProtocol: requester,
                GetExamWorkspaceAnswerKeySuggestionsStatusHandlerProtocol: status,
            },
        )
        app = FastAPI()
        app.middleware("http")(error_handler_middleware)
        app.include_router(documents_api.router)
        app.include_router(suggestions_api.router)
        app.dependency_overrides[require_app_user_api] = lambda: actor
        setup_dishka(container, app)
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    _BASE + "/import-digiexam",
                    files={
                        "file": (FIXTURE.name, FIXTURE.read_bytes(), "application/octet-stream")
                    },
                    data={"course_key": "SVESVE02"},
                )
                assert response.status_code == 202, response.text
                imported = response.json()
                lineage_id = UUID(imported["lineage_id"])
                async with world.uow:
                    job = await world.jobs.claim_next(
                        worker_id="dxe-import", now=clock.now(), lease_ttl=timedelta(minutes=5)
                    )
                assert job is not None and str(job.id) == imported["job_id"]
                finished = await ProcessExamWorkspaceDigiExamJobHandler(
                    jobs=world.jobs,
                    store=world.store,
                    users=PostgreSQLUserRepository(session),
                    uow=world.uow,
                    clock=clock,
                    id_generator=Ids(),
                    codec=world.codec,
                    image_decodability=PillowEmbeddedImageDecodability(),
                ).handle(job=job)
                assert finished.status.value == "succeeded"
                document = await world.open(actor, lineage_id)
                assert document.origin.kind == "digiexam_import"
                assert len(document.items) == 8
                # Import itself must not automatically enqueue a suggestion job.
                assert (
                    await world.jobs.get_latest_workspace_job(
                        owner_user_id=actor.id,
                        workspace_lineage_id=lineage_id,
                        workspace_document_revision=document.revision,
                    )
                    is None
                )
                path = f"{_BASE}/documents/{lineage_id}/answer-key-suggestions"
                body = {"document": document.model_dump(mode="json")}
                whole = await client.post(path, json=body)
                assert whole.status_code == 200, whole.text
                whole_id = whole.json()["job_id"]
                assert whole.json()["state"] == "queued"
                duplicate = await client.post(path, json=body)
                assert duplicate.status_code == 200, duplicate.text
                assert duplicate.json()["job_id"] == whole_id
                single_body = {**body, "item_id": document.items[1].item_id}
                single = await client.post(path, json=single_body)
                assert single.status_code == 200, single.text
                single_id = single.json()["job_id"]
                assert single_id != whole_id
                duplicate = await client.post(path, json=single_body)
                assert duplicate.status_code == 200, duplicate.text
                assert duplicate.json()["job_id"] == single_id

                model = CapturingModel()
                lane = ExamAnswerKeyEnrichmentWorkspaceLane(
                    enrichment_jobs=world.jobs,
                    provider_selector=FixedRouteAnswerKeyProviderSelector(route=_route()),
                    uow=world.uow,
                    clock=clock,
                    ledger=AnswerKeyAttemptLedger(
                        enrichment_jobs=world.jobs,
                        attempts=AnswerKeyProviderAttemptRunner(provider=model),
                        uow=world.uow,
                        clock=clock,
                    ),
                )
                for job_id, count in [(whole_id, 6), (single_id, 1)]:
                    async with world.uow:
                        claimed = await world.jobs.claim_next(
                            worker_id="suggestions", now=clock.now(), lease_ttl=timedelta(minutes=5)
                        )
                    assert claimed is not None and str(claimed.id) == job_id
                    assert claimed.source_kind.value == "workspace"
                    views = WorkspaceAnswerKeyRequestPayload.model_validate(
                        claimed.workspace_request_json
                    )
                    assert len(views.views) == count
                    result = await lane.handle(job=claimed)
                    assert result.status.value == "succeeded"
                    response = await client.get(path + "/" + job_id)
                    assert response.status_code == 200, response.text
                    assert response.json()["state"] == "succeeded"
                    arrived = ExamWorkspaceAnswerKeySuggestionsResponse.model_validate(
                        response.json()
                    )
                    if count == 6:
                        assert_item_local_suggestions(document, arrived.suggestions)
                    else:
                        assert [entry.item_id for entry in arrived.suggestions] == [
                            document.items[1].item_id
                        ]
                assert model.call_count == 7
                # The persisted document still has absent keys; worker results need teacher review.
                assert await world.open(actor, lineage_id) == document
                revision_two = await world.teacher_save(actor, document)
                response = await client.post(
                    path,
                    json={
                        "document": revision_two.document.model_dump(mode="json"),
                        "item_id": document.items[1].item_id,
                    },
                )
                assert response.status_code == 200, response.text
                assert response.json()["job_id"] not in {whole_id, single_id}
                # Simulated teacher-sent source key: explicit requests must not enqueue at all.
                keyed = document.model_dump(mode="json")
                keyed["items"][1]["answer_key"] = {
                    "origin": "source_provided",
                    "correct_choice_ids": ["choice_001"],
                    "match_pairs": [],
                }
                response = await client.post(
                    path,
                    json={
                        "document": NativeExamDocument.model_validate(keyed).model_dump(
                            mode="json"
                        ),
                        "item_id": document.items[1].item_id,
                    },
                )
                assert response.status_code == 200, response.text
                assert response.json()["state"] == "not_eligible"
                assert response.json()["job_id"] is None
        finally:
            await container.close()
