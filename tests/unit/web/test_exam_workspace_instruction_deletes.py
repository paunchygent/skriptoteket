"""Delete HTTP commands over saved conversion output and the real editor seam.

This is in-memory HTTP/codec proof, not a browser or Exam.net acceptance walk.
"""

from unittest.mock import Mock

import httpx
import pytest
from dishka import AsyncContainer, make_async_container
from fastapi import FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceDocumentResponse,
)
from skriptoteket.application.curated_apps.exam_workspace_history import (
    ExamWorkspaceHistoryDocumentResponse,
    ExamWorkspaceHistoryResponse,
    ExamWorkspaceUndoStepResponse,
    StoreExamWorkspaceUndoStepRequest,
)
from skriptoteket.application.curated_apps.exam_workspace_parents import ExamWorkspaceDeleteResponse
from skriptoteket.application.curated_apps.handlers.exam_workspace_parents import (
    ExamWorkspaceParentsHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import NativeExamParent
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace import (
    ExportExamWorkspaceDocumentHandlerProtocol,
    GetExamWorkspaceDocumentHandlerProtocol,
    SaveExamWorkspaceDocumentHandlerProtocol,
)
from skriptoteket.protocols.exam_workspace_history import StoreExamWorkspaceUndoStepHandlerProtocol
from skriptoteket.protocols.exam_workspace_parents import ExamWorkspaceParentsHandlerProtocol
from skriptoteket.web.api.v1 import apps_conversion_hub_exam_workspace as documents_api
from skriptoteket.web.api.v1 import apps_conversion_hub_exam_workspace_parents as parents_api
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _actor,
    _Env,
    _leased_tab,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_history_contract import (
    _undo_handler,
)
from tests.unit.domain.curated_apps.exam_workspace.recorded_native_exam_support import (
    parent_over,
    recorded_items,
)
from tests.unit.web.test_apps_exam_workspace_answer_key_suggestions_api import FakeRegistry
from tests.unit.web.test_apps_exam_workspace_parent_skeleton import SkeletonProvider


async def _saved_conversion(
    env: _Env, actor: User, *, last_child: bool, only_parent: bool = False
) -> ExamWorkspaceDocumentResponse:
    imported = await env.seed_document(actor=actor)
    # Recorded model-produced mixed question kinds, not teacher-created children.
    parents: tuple[NativeExamParent, ...] = (
        parent_over("parent_001", "Converted instruction", *((2,) if last_child else (2, 3, 4))),
        parent_over("parent_002", "Unchanged instruction", 6, 7),
    )
    items = recorded_items()
    if only_parent:
        child_count = 1 if last_child else 3
        items = items[:child_count]
        parents = (parent_over("parent_001", "Only instruction", *range(1, child_count + 1)),)
    document = NativeExamDocument.model_validate(
        dict(imported.document.model_dump(), revision=2, items=items, parents=parents)
    )
    history = await env.save_handler.history(actor=actor, lineage_id=document.document_id)
    await _undo_handler(env).handle(
        actor=actor,
        lineage_id=document.document_id,
        request=StoreExamWorkspaceUndoStepRequest(
            tab_id=await _leased_tab(env, actor, document.document_id),
            expected_cursor=history.cursor,
            document=document,
        ),
    )
    return await env.get_handler.handle(actor=actor, lineage_id=document.document_id)


def _app(
    env: _Env, actor: User, undo_steps: StoreExamWorkspaceUndoStepHandlerProtocol
) -> tuple[FastAPI, AsyncContainer]:
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
    app.include_router(documents_api.router)
    app.include_router(parents_api.router)
    app.dependency_overrides[require_app_user_api] = lambda: actor
    setup_dishka(container, app)
    return app, container


@pytest.mark.parametrize("command", ["heading", "cascade", "child", "last-child"])
async def test_delete_is_one_guarded_undo_step_and_writes_the_file(command: str) -> None:
    env = _Env()
    actor = _actor()
    saved = await _saved_conversion(env, actor, last_child=command == "last-child")
    lineage_id = saved.document.document_id
    undo_steps = _undo_handler(env)
    # Force a newer unsaved step; the delete must start from the saved file.
    before = saved.document.model_copy(update={"title": "Unsaved draft retained by delete"})
    initial = await undo_steps.handle(
        actor=actor,
        lineage_id=lineage_id,
        request=StoreExamWorkspaceUndoStepRequest(
            tab_id=await _leased_tab(env, actor, lineage_id),
            expected_cursor=saved.history_cursor,
            document=before,
        ),
    )
    vault_file = env.vault_files.files[saved.summary.vault_file_id]
    app, container = _app(env, actor, undo_steps)
    path = f"/api/v1/apps/documents.conversion_hub/exam-workspace/documents/{lineage_id}"
    suffix = {
        "heading": "",
        "cascade": "/with-children",
        "child": "/children/item_002",
        "last-child": "/children/item_002",
    }[command]
    delete_path = path + "/parents/parent_001" + suffix
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            # The unsaved step already overwrote the file: the delete starts from it.
            unsaved_file = env.codec.parse(
                content=await env.store.load(actor=actor, vault_file=vault_file)
            )
            assert unsaved_file.document == initial.document
            tab = str(await _leased_tab(env, actor, lineage_id))
            result = await _exercise_delete(client, path, delete_path, saved, initial, command, tab)
            deleted_file = env.codec.parse(
                content=await env.store.load(actor=actor, vault_file=vault_file)
            )
            assert deleted_file.document == result.document
            await _undo_delete(client, path, initial, result, tab)
            restored_file = env.codec.parse(
                content=await env.store.load(actor=actor, vault_file=vault_file)
            )
            reopened = ExamWorkspaceDocumentResponse.model_validate((await client.get(path)).json())
            assert restored_file.document == reopened.document
            assert reopened.document == initial.document.model_copy(
                update={"revision": reopened.summary.version}
            )
    finally:
        await container.close()


@pytest.mark.parametrize("last_child", [False, True], ids=["cascade", "last-child"])
async def test_removing_every_question_returns_named_error_without_storing_a_step(
    last_child: bool,
) -> None:
    env = _Env()
    actor = _actor()
    saved = await _saved_conversion(env, actor, last_child=last_child, only_parent=True)
    app, container = _app(env, actor, _undo_handler(env))
    lineage_id = saved.document.document_id
    path = f"/api/v1/apps/documents.conversion_hub/exam-workspace/documents/{lineage_id}"
    suffix = "/children/item_001" if last_child else "/with-children"
    vault_file = env.vault_files.files[saved.summary.vault_file_id]
    original_bytes = await env.store.load(actor=actor, vault_file=vault_file)
    tab = str(await _leased_tab(env, actor, lineage_id))
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            history_before = await client.get(path + "/history")
            response = await client.request(
                "DELETE",
                path + "/parents/parent_001" + suffix,
                json={"expected_cursor": str(saved.history_cursor), "tab_id": tab},
            )
            assert response.status_code == 422, response.text
            assert response.json()["error"] == {
                "code": "VALIDATION_ERROR",
                "message": "Provet måste ha minst en fråga.",
                "details": {"reason": "exam_requires_question", "parent_id": "parent_001"},
            }
            assert (await client.get(path + "/history")).json() == history_before.json()
            reopened = ExamWorkspaceDocumentResponse.model_validate((await client.get(path)).json())
            assert reopened.document == saved.document
            assert reopened.history_cursor == saved.history_cursor
            assert await env.store.load(actor=actor, vault_file=vault_file) == original_bytes
    finally:
        await container.close()


async def _exercise_delete(
    client: httpx.AsyncClient,
    path: str,
    delete_path: str,
    saved: ExamWorkspaceDocumentResponse,
    initial: ExamWorkspaceUndoStepResponse,
    command: str,
    tab: str,
) -> ExamWorkspaceDeleteResponse:
    before = initial.document
    # A matching file revision is irrelevant when the editor cursor is stale.
    stale = await client.request(
        "DELETE", delete_path, json={"expected_cursor": str(saved.history_cursor), "tab_id": tab}
    )
    assert stale.status_code == 409, stale.text
    assert stale.json()["error"]["code"] == "CONFLICT"
    assert (await client.get(path)).json()["document"] == before.model_dump(mode="json")
    response = await client.request(
        "DELETE", delete_path, json={"expected_cursor": str(initial.history.cursor), "tab_id": tab}
    )
    assert response.status_code == 200, response.text
    result = ExamWorkspaceDeleteResponse.model_validate(response.json())
    assert result.removed_parent_id == ("parent_001" if command in {"heading", "cascade"} else None)
    assert result.document.title == before.title
    assert result.saved_document == result.document
    assert result.summary.version == saved.summary.version + 2
    untouched = before.parents[-1]
    after_untouched = next(
        parent for parent in result.document.parents if parent.parent_id == untouched.parent_id
    )
    assert after_untouched.item_ids == untouched.item_ids
    assert after_untouched.instruction == untouched.instruction
    assert after_untouched.place == result.document.item_by_id(untouched.item_ids[0]).sequence - 1
    assert result.history_cursor != initial.history.cursor
    _assert_deletion(before, result.document, command)
    history = ExamWorkspaceHistoryResponse.model_validate(
        (await client.get(path + "/history")).json()
    )
    assert history.step_ids == (*initial.history.step_ids, result.history_cursor)
    # A duplicate request cannot create another step or turn into a NOT_FOUND answer.
    duplicate = await client.request(
        "DELETE",
        delete_path,
        json={"expected_cursor": str(initial.history.cursor), "tab_id": tab},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "CONFLICT"
    unchanged_history = await client.get(path + "/history")
    assert ExamWorkspaceHistoryResponse.model_validate(unchanged_history.json()) == history
    return result


async def _undo_delete(
    client: httpx.AsyncClient,
    path: str,
    initial: ExamWorkspaceUndoStepResponse,
    result: ExamWorkspaceDeleteResponse,
    tab: str,
) -> None:
    deleted = ExamWorkspaceDocumentResponse.model_validate((await client.get(path)).json())
    previous = await client.get(path + "/history/" + str(initial.history.cursor))
    predecessor = ExamWorkspaceHistoryDocumentResponse.model_validate(previous.json())
    assert predecessor.document == initial.document.model_copy(
        update={"revision": deleted.summary.version}
    )
    undone = await client.post(
        path + "/autosaves",
        json={
            "expected_cursor": str(result.history_cursor),
            "after_step_id": str(predecessor.step_id),
            "document": predecessor.document.model_dump(mode="json"),
            "tab_id": tab,
        },
    )
    assert undone.status_code == 200, undone.text
    restored = ExamWorkspaceUndoStepResponse.model_validate(undone.json())
    reopened = ExamWorkspaceDocumentResponse.model_validate((await client.get(path)).json())
    assert restored.document == reopened.document
    assert reopened.document == initial.document.model_copy(
        update={"revision": reopened.summary.version}
    )
    assert result.history_cursor not in restored.history.step_ids


def _assert_deletion(before: NativeExamDocument, after: NativeExamDocument, command: str) -> None:
    NativeExamDocument.model_validate(after.model_dump())
    assert [i.sequence for i in after.items] == list(range(1, len(after.items) + 1))
    if command == "heading":
        assert after.items == before.items
        assert all(after.parent_of(i) is None for i in before.parents[0].item_ids)
    elif command == "last-child":
        kept = next(parent for parent in after.parents if parent.parent_id == "parent_001")
        assert kept.item_ids == (), "A part that loses its last child stays (G8)"
        assert after.parent_of("item_002") is None
        expected = [item for item in before.items if item.item_id != "item_002"]
        assert after.items == tuple(
            item.model_copy(update={"sequence": sequence})
            for sequence, item in enumerate(expected, 1)
        )
    else:
        removed = set(before.parents[0].item_ids) if command == "cascade" else {"item_002"}
        expected = [item for item in before.items if item.item_id not in removed]
        assert after.items == tuple(
            item.model_copy(update={"sequence": sequence})
            for sequence, item in enumerate(expected, 1)
        )
