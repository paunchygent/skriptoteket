"""A blank exam title is a savable draft state that only export refuses (TASK-SKRIPT-40-04-05).

In-memory HTTP proof through the real request schemas, not a browser walk: the earlier
handler tests built blank-title documents with `model_copy`, which skips validation, so a
request-schema title guard went unseen until the staging walk.
"""

import httpx
import pytest

from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceDocumentResponse
from skriptoteket.application.curated_apps.exam_workspace_history import (
    ExamWorkspaceUndoStepResponse,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    NativeExportBlocker,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _actor,
    _Env,
    _leased_tab,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_history_contract import (
    _undo_handler,
)
from tests.unit.web.test_exam_workspace_instruction_deletes import _app

_TITLE_BLOCKER = NativeExportBlocker(item_id=None, reason="title_without_text")


@pytest.mark.parametrize("title", ["", "   "])
async def test_autosave_stores_a_blank_title_and_returns_the_title_blocker(title: str) -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    app, container = _app(env, actor, _undo_handler(env))
    tab = str(await _leased_tab(env, actor, imported.summary.lineage_id))
    path = (
        "/api/v1/apps/documents.conversion_hub/exam-workspace/documents/"
        f"{imported.summary.lineage_id}"
    )
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            blank = await client.post(
                path + "/autosaves",
                json={
                    "expected_cursor": str(imported.history_cursor),
                    "document": imported.document.model_dump(mode="json") | {"title": title},
                    "tab_id": tab,
                },
            )
            assert blank.status_code == 200, blank.text
            stored = ExamWorkspaceUndoStepResponse.model_validate(blank.json())
            assert stored.document.title == title
            assert _TITLE_BLOCKER in stored.export_blockers
            assert blank.json()["export_blockers"][0] == {
                "item_id": None,
                "reason": "title_without_text",
            }

            reopened = ExamWorkspaceDocumentResponse.model_validate((await client.get(path)).json())
            assert reopened.document.title == title
            assert _TITLE_BLOCKER in reopened.export_blockers

            titled = await client.post(
                path + "/autosaves",
                json={
                    "expected_cursor": str(stored.history.cursor),
                    "document": imported.document.model_dump(mode="json") | {"title": "Prov 1"},
                    "tab_id": tab,
                },
            )
            assert titled.status_code == 200, titled.text
            assert _TITLE_BLOCKER not in (
                ExamWorkspaceUndoStepResponse.model_validate(titled.json()).export_blockers
            )
    finally:
        await container.close()
