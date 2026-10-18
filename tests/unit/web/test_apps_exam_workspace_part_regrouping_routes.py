"""HTTP/DI skeleton for the exam-workspace group, empty-part and move routes."""

from unittest.mock import Mock
from uuid import uuid4

import httpx
from dishka import make_async_container
from fastapi import FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceDocumentResponse
from skriptoteket.application.curated_apps.exam_workspace_parents import (
    ExamWorkspaceCreatedPartResponse,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_parents import (
    ExamWorkspaceParentsHandler,
)
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace import (
    ExportExamWorkspaceDocumentHandlerProtocol,
    GetExamWorkspaceDocumentHandlerProtocol,
    SaveExamWorkspaceDocumentHandlerProtocol,
)
from skriptoteket.protocols.exam_workspace_history import StoreExamWorkspaceUndoStepHandlerProtocol
from skriptoteket.protocols.exam_workspace_parents import ExamWorkspaceParentsHandlerProtocol
from skriptoteket.web.api.v1 import apps_conversion_hub_exam_workspace_parents as parents_api
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _actor,
    _Env,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_history_contract import (
    _undo_handler,
)
from tests.unit.web.parent_skeleton_test_support import SkeletonProvider
from tests.unit.web.test_apps_exam_workspace_answer_key_suggestions_api import FakeRegistry


async def test_group_empty_and_move_routes_are_guarded_undoable_and_named() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage_id = imported.document.document_id
    undo_steps = _undo_handler(env)
    handler = ExamWorkspaceParentsHandler(reader=env.get_handler, undo_steps=undo_steps)
    container = make_async_container(
        SkeletonProvider(),
        context={
            CuratedAppRegistryProtocol: FakeRegistry(),
            GetExamWorkspaceDocumentHandlerProtocol: env.get_handler,
            SaveExamWorkspaceDocumentHandlerProtocol: env.save_handler,
            ExamWorkspaceParentsHandlerProtocol: handler,
            StoreExamWorkspaceUndoStepHandlerProtocol: undo_steps,
            ExportExamWorkspaceDocumentHandlerProtocol: Mock(
                spec=ExportExamWorkspaceDocumentHandlerProtocol
            ),
        },
    )
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(parents_api.router)
    app.dependency_overrides[require_app_user_api] = lambda: actor
    setup_dishka(container, app)
    path = f"/api/v1/apps/documents.conversion_hub/exam-workspace/documents/{lineage_id}/parents"
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            cursor = (
                await env.get_handler.handle(actor=actor, lineage_id=lineage_id)
            ).history_cursor
            stale = await client.post(
                path + "/group",
                json={"expected_cursor": str(uuid4()), "item_ids": ["item_001", "item_003"]},
            )
            assert stale.status_code == 409, stale.text
            assert stale.json()["error"]["code"] == "CONFLICT"

            grouped_response = await client.post(
                path + "/group",
                json={"expected_cursor": str(cursor), "item_ids": ["item_001", "item_003"]},
            )
            assert grouped_response.status_code == 200, grouped_response.text
            grouped = ExamWorkspaceCreatedPartResponse.model_validate(grouped_response.json())
            assert grouped.created_parent_id in {p.parent_id for p in grouped.document.parents}
            grouped_part = next(
                p for p in grouped.document.parents if p.parent_id == grouped.created_parent_id
            )
            assert grouped_part.item_ids == ("item_001", "item_003")

            empty_response = await client.post(
                path + "/empty",
                json={"expected_cursor": str(grouped.history_cursor), "position": 0},
            )
            assert empty_response.status_code == 200, empty_response.text
            emptied = ExamWorkspaceCreatedPartResponse.model_validate(empty_response.json())
            assert emptied.created_parent_id != grouped.created_parent_id
            new_part = next(
                p for p in emptied.document.parents if p.parent_id == emptied.created_parent_id
            )
            assert new_part.item_ids == ()

            move_in_response = await client.post(
                path + "/move",
                json={
                    "expected_cursor": str(emptied.history_cursor),
                    "item_id": "item_005",
                    "target_parent_id": grouped.created_parent_id,
                },
            )
            assert move_in_response.status_code == 200, move_in_response.text
            moved_in = ExamWorkspaceDocumentResponse.model_validate(move_in_response.json())
            moved_part = next(
                p for p in moved_in.document.parents if p.parent_id == grouped.created_parent_id
            )
            assert moved_part.item_ids == ("item_001", "item_003", "item_005")

            move_out_response = await client.post(
                path + "/move",
                json={
                    "expected_cursor": str(moved_in.history_cursor),
                    "item_id": "item_005",
                    "target_parent_id": None,
                },
            )
            assert move_out_response.status_code == 200, move_out_response.text
            moved_out = ExamWorkspaceDocumentResponse.model_validate(move_out_response.json())
            assert moved_out.document.parent_of("item_005") is None

            in_part = await client.post(
                path + "/group",
                json={"expected_cursor": str(moved_out.history_cursor), "item_ids": ["item_001"]},
            )
            assert in_part.status_code == 422, in_part.text
            assert in_part.json()["error"]["details"]["reason"] == "item_in_part"

            standalone = await client.post(
                path + "/move",
                json={
                    "expected_cursor": str(moved_out.history_cursor),
                    "item_id": "item_005",
                    "target_parent_id": None,
                },
            )
            assert standalone.status_code == 422, standalone.text
            assert standalone.json()["error"]["details"]["reason"] == "already_standalone"

            unknown_part = await client.post(
                path + "/move",
                json={
                    "expected_cursor": str(moved_out.history_cursor),
                    "item_id": "item_005",
                    "target_parent_id": "parent_999",
                },
            )
            assert unknown_part.status_code == 404, unknown_part.text
            assert unknown_part.json()["error"]["code"] == "NOT_FOUND"

            unmarked = await client.post(
                path + "/group",
                json={"expected_cursor": str(moved_out.history_cursor), "item_ids": []},
            )
            assert unmarked.status_code == 422, unmarked.text
            assert "detail" in unmarked.json()
    finally:
        await container.close()
