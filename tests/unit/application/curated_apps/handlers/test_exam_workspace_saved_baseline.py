"""Reopening exposes the stored undo step as the durable exam."""

import pytest

from skriptoteket.application.curated_apps.exam_workspace_history import (
    StoreExamWorkspaceUndoStepRequest,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _actor,
    _Env,
    _leased_tab,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_history_contract import (
    _undo_handler,
)


@pytest.mark.asyncio
async def test_reopen_shows_the_stored_step_as_both_document_and_saved_exam() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    initial = await env.get_handler.handle(actor=actor, lineage_id=lineage)
    assert initial.saved_document == initial.document
    history = await env.save_handler.history(actor=actor, lineage_id=lineage)
    working = imported.document.model_copy(update={"title": "Lärarens arbetskopia"})
    await _undo_handler(env).handle(
        actor=actor,
        lineage_id=lineage,
        request=StoreExamWorkspaceUndoStepRequest(
            expected_cursor=history.cursor,
            document=working,
            tab_id=await _leased_tab(env, actor, lineage),
        ),
    )

    reopened = await env.get_handler.handle(actor=actor, lineage_id=lineage)
    assert reopened.document == working.model_copy(update={"revision": 2})
    assert reopened.saved_document == reopened.document
    assert reopened.saved_document.revision == reopened.summary.version == 2
