"""Reopening exposes the durable exam separately from the teacher's undo copy."""

import pytest

from skriptoteket.application.curated_apps.exam_workspace import SaveExamWorkspaceDocumentRequest
from skriptoteket.application.curated_apps.exam_workspace_history import (
    StoreExamWorkspaceUndoStepRequest,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _actor,
    _Env,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_history_contract import (
    _undo_handler,
)


@pytest.mark.asyncio
async def test_reopen_and_save_keep_saved_exam_distinct_from_autosave() -> None:
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
        request=StoreExamWorkspaceUndoStepRequest(expected_cursor=history.cursor, document=working),
    )

    reopened = await env.get_handler.handle(actor=actor, lineage_id=lineage)
    assert reopened.document == working
    assert reopened.saved_document == imported.document
    assert reopened.saved_document.revision == reopened.summary.version == 1

    saved = await env.save_handler.handle(
        actor=actor,
        lineage_id=lineage,
        request=SaveExamWorkspaceDocumentRequest(
            expected_revision=1,
            document=reopened.document.model_copy(update={"revision": 2}),
        ),
    )
    assert saved.saved_document == saved.document
    assert saved.saved_document.title == working.title
    assert saved.saved_document.revision == 2
    after_save = await env.get_handler.handle(actor=actor, lineage_id=lineage)
    assert after_save.saved_document == after_save.document == saved.document
