"""Real PostgreSQL + HTTP + production DI proof: one retype, one autosave, one undo."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from dishka import Provider, Scope, from_context, make_async_container
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    GetExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_undo_steps import (
    StoreExamWorkspaceUndoStepHandler,
)
from skriptoteket.di.exam_workspace_change_type import ExamWorkspaceChangeTypeProvider
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace import (
    GetExamWorkspaceDocumentHandlerProtocol,
    SaveExamWorkspaceDocumentHandlerProtocol,
)
from skriptoteket.protocols.exam_workspace_history import StoreExamWorkspaceUndoStepHandlerProtocol
from skriptoteket.web.api.v1 import apps_conversion_hub_exam_workspace as documents_api
from skriptoteket.web.api.v1 import apps_conversion_hub_exam_workspace_change_type as change_api
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.exam_workspace_conversion_support import ConversionWorld, Ids
from tests.integration.exam_workspace_repair_support import editor, seed_exam
from tests.integration.infrastructure.repositories.exam_workspace_test_support import create_owner
from tests.unit.domain.curated_apps.exam_workspace.inline_choice_test_support import (
    inline_choice_item,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_gap_fill_item,
)
from tests.unit.domain.curated_apps.exam_workspace.recorded_native_exam_support import parent_over
from tests.unit.web.test_apps_exam_workspace_answer_key_suggestions_api import FakeRegistry

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]
_BASE = "/api/v1/apps/documents.conversion_hub/exam-workspace/documents/"


class PersistenceApiProvider(Provider):
    registry = from_context(provides=CuratedAppRegistryProtocol, scope=Scope.APP)
    reader = from_context(provides=GetExamWorkspaceDocumentHandlerProtocol, scope=Scope.APP)
    writer = from_context(provides=SaveExamWorkspaceDocumentHandlerProtocol, scope=Scope.APP)
    steps = from_context(provides=StoreExamWorkspaceUndoStepHandlerProtocol, scope=Scope.APP)


@asynccontextmanager
async def _client(world: ConversionWorld, actor: User) -> AsyncIterator[httpx.AsyncClient]:
    container = make_async_container(
        PersistenceApiProvider(),
        ExamWorkspaceChangeTypeProvider(),
        context={
            CuratedAppRegistryProtocol: FakeRegistry(),
            GetExamWorkspaceDocumentHandlerProtocol: GetExamWorkspaceDocumentHandler(
                vault_files=world.vault_files,
                codec=world.codec,
                store=world.store,
                jobs=world.jobs,
                uow=world.uow,
            ),
            SaveExamWorkspaceDocumentHandlerProtocol: editor(world),
            StoreExamWorkspaceUndoStepHandlerProtocol: StoreExamWorkspaceUndoStepHandler(
                vault_files=world.vault_files,
                codec=world.codec,
                store=world.store,
                id_generator=Ids(),
                jobs=world.jobs,
            ),
        },
    )
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(documents_api.router)
    app.include_router(change_api.router)
    app.dependency_overrides[require_app_user_api] = lambda: actor
    setup_dishka(container, app)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client
    finally:
        await container.close()


@pytest.mark.parametrize("parented", [False, True], ids=["standalone", "child"])
@pytest.mark.parametrize("source_kind", ["gap_fill", "inline_choice"])
async def test_change_reopens_as_one_autosave_and_one_undo_restores_exact_question(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    parented: bool,
    source_kind: str,
) -> None:
    actor = await create_owner(session_factory)
    clock = FixedClock(datetime.now(UTC))
    storage = LocalVaultStorage(vault_root=tmp_path)
    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        seeded = await seed_exam(world, actor)
        question = (
            make_gap_fill_item() if source_kind == "gap_fill" else inline_choice_item(points=2)
        )
        prepared = NativeExamDocument.model_validate(
            {
                **seeded.model_dump(),
                "revision": 2,
                "items": (question,),
                "parents": (parent_over("parent_001", "Gemensam instruktion", 1),)
                if parented
                else (),
            }
        )
        path = _BASE + str(prepared.document_id)
        async with _client(world, actor) as client:
            response = await client.put(
                path, json={"expected_revision": 1, "document": prepared.model_dump(mode="json")}
            )
            assert response.status_code == 200, response.text
            saved = response.json()
            # A prior unsaved edit catches handlers which retype the file instead of editor state.
            draft = prepared.model_copy(update={"title": "Teacher's unsaved title"})
            response = await client.post(
                path + "/autosaves",
                json={
                    "expected_cursor": saved["history_cursor"],
                    "document": draft.model_dump(mode="json"),
                },
            )
            assert response.status_code == 200, response.text
            previous = response.json()
            before_history = previous["history"]
            command = {
                "item_id": question.item_id,
                "target_kind": "free_text",
                "expected_revision": 2,
                "expected_cursor": before_history["cursor"],
            }
            response = await client.post(
                path + "/change-type", json={**command, "expected_revision": 1}
            )
            assert response.status_code == 409, response.text
            assert response.json()["error"]["code"] == "CONFLICT"
            assert (await client.get(path + "/history")).json() == before_history
            response = await client.post(path + "/change-type", json=command)
            assert response.status_code == 200, response.text
            changed = response.json()
            expected_drop = (
                {"gaps", "accepted_values"}
                if source_kind == "gap_fill"
                else {"gaps", "options", "correct_option_id"}
            )
            assert set(changed["dropped_content"]) == expected_drop
            actual = NativeExamDocument.model_validate(changed["document"])
            assert actual.title == draft.title
            assert actual.parents == prepared.parents
            assert actual.items[0].kind is NativeExamItemKind.FREE_TEXT
            assert actual.items[0].points == 2
            assert actual.items[0].gaps == ()
            assert actual.revision == 2
            assert changed["saved_document"] == saved["document"]
            history = (await client.get(path + "/history")).json()
            assert history["step_ids"][:-1] == before_history["step_ids"]
            assert len(history["step_ids"]) == len(before_history["step_ids"]) + 1
            assert history["cursor"] == changed["history_cursor"]
            # Revision remains 2, so a repeated request must be rejected by the cursor guard.
            response = await client.post(path + "/change-type", json=command)
            assert response.status_code == 409, response.text
            assert response.json()["error"]["code"] == "CONFLICT"
            assert (await client.get(path + "/history")).json() == history

    # Fresh DB session, handlers and DI prove persistence rather than an in-process cache.
    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        async with _client(world, actor) as client:
            reopened = await client.get(path)
            assert reopened.status_code == 200, reopened.text
            assert reopened.json()["document"] == changed["document"]
            head = await world.vault_files.get_document_head(
                user_id=actor.id, document_lineage_id=prepared.document_id
            )
            assert head is not None and head.document_version == 2
            persisted = world.codec.parse(
                content=await world.store.load(actor=actor, vault_file=head)
            )
            assert persisted.document == prepared, "Autosave cannot overwrite Spara's baseline"
            response = await client.get(path + "/history/" + before_history["cursor"])
            assert response.status_code == 200, response.text
            undo = response.json()
            assert undo["document"] == draft.model_dump(mode="json")
            response = await client.post(
                path + "/autosaves",
                json={
                    "expected_cursor": history["cursor"],
                    "after_step_id": undo["step_id"],
                    "document": undo["document"],
                },
            )
            assert response.status_code == 200, response.text
            restored = response.json()
            assert restored["document"] == draft.model_dump(mode="json")
            assert restored["document"]["items"][0] == question.model_dump(mode="json")
            assert changed["history_cursor"] not in restored["history"]["step_ids"]
            assert (await client.get(path)).json()["document"] == restored["document"]

    async with session_factory() as session:
        async with _client(ConversionWorld(session, storage, clock), actor) as client:
            response = await client.get(path)
            assert response.status_code == 200, response.text
            assert response.json()["document"] == restored["document"]
