"""The editor's position in its undo history, separate from the concurrency cursor."""

from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.exam_workspace import SaveExamWorkspaceDocumentRequest
from skriptoteket.application.curated_apps.exam_workspace_history import (
    ExamWorkspaceHistoryState,
    ExamWorkspaceHistoryStep,
    StoreExamWorkspaceUndoStepRequest,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _actor,
    _Env,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_history_contract import (
    _handler,
    _undo_handler,
)


async def _autosave(env: _Env, actor, lineage, document) -> None:
    cursor = (await _handler(env).history(actor=actor, lineage_id=lineage)).cursor
    await _undo_handler(env).handle(
        actor=actor,
        lineage_id=lineage,
        request=StoreExamWorkspaceUndoStepRequest(expected_cursor=cursor, document=document),
    )


async def _spara(env: _Env, actor, lineage, document, expected_revision: int) -> None:
    await _handler(env).handle(
        actor=actor,
        lineage_id=lineage,
        request=SaveExamWorkspaceDocumentRequest(
            expected_revision=expected_revision,
            document=document.model_copy(update={"revision": expected_revision + 1}),
        ),
    )


@pytest.mark.asyncio
async def test_a_fresh_import_stands_on_its_baseline() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    history = await _handler(env).history(actor=actor, lineage_id=imported.summary.lineage_id)
    assert history.step_ids == ()
    assert history.position_step_id == history.baseline_step_id


@pytest.mark.asyncio
async def test_spara_of_the_autosaved_copy_keeps_the_position_on_its_step() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    edited = imported.document.model_copy(update={"title": "Första"})
    await _autosave(env, actor, lineage, edited)
    await _autosave(env, actor, lineage, edited.model_copy(update={"title": "Andra"}))
    before = await _handler(env).history(actor=actor, lineage_id=lineage)

    await _spara(env, actor, lineage, edited.model_copy(update={"title": "Andra"}), 1)

    after = await _handler(env).history(actor=actor, lineage_id=lineage)
    # The cursor rotates for concurrency, but it names no step; the position does.
    assert after.cursor != before.cursor
    assert after.cursor not in (after.baseline_step_id, *after.step_ids)
    assert after.step_ids == before.step_ids
    assert after.position_step_id == before.step_ids[-1]


@pytest.mark.asyncio
async def test_spara_after_undo_stands_on_the_undone_step() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    first = imported.document.model_copy(update={"title": "Första"})
    await _autosave(env, actor, lineage, first)
    await _autosave(env, actor, lineage, first.model_copy(update={"title": "Andra"}))
    before = await _handler(env).history(actor=actor, lineage_id=lineage)

    # The editor undid to "Första" (a read only) and saves that copy.
    await _spara(env, actor, lineage, first, 1)

    after = await _handler(env).history(actor=actor, lineage_id=lineage)
    assert after.step_ids == before.step_ids
    assert after.position_step_id == before.step_ids[0]
    reopened = await env.get_handler.handle(actor=actor, lineage_id=lineage)
    assert reopened.document.title == "Första"


@pytest.mark.asyncio
async def test_spara_of_an_unmodified_import_keeps_the_position_on_the_baseline() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    await _spara(env, actor, lineage, imported.document, 1)
    history = await _handler(env).history(actor=actor, lineage_id=lineage)
    assert history.position_step_id == history.baseline_step_id


@pytest.mark.asyncio
async def test_spara_of_an_unretained_copy_retains_it_before_the_next_edit() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    await _autosave(env, actor, lineage, imported.document.model_copy(update={"title": "Steg"}))
    saved = imported.document.model_copy(update={"title": "Aldrig autosparad"})

    await _spara(env, actor, lineage, saved, 1)

    after_save = await _handler(env).history(actor=actor, lineage_id=lineage)
    assert after_save.position_step_id is None
    await _autosave(env, actor, lineage, saved.model_copy(update={"title": "Nästa"}))
    after_edit = await _handler(env).history(actor=actor, lineage_id=lineage)
    assert after_edit.position_step_id == after_edit.step_ids[-1]
    titles = [
        (
            await _handler(env).history_step(actor=actor, lineage_id=lineage, step_id=step)
        ).document.title
        for step in after_edit.step_ids
    ]
    assert titles == ["Steg", "Aldrig autosparad", "Nästa"]


def test_the_position_must_name_a_retained_snapshot() -> None:
    baseline = ExamWorkspaceHistoryStep(step_id=uuid4(), content=b"baseline")
    ExamWorkspaceHistoryState(cursor=uuid4(), current_step_id=baseline.step_id, baseline=baseline)
    with pytest.raises(ValueError):
        ExamWorkspaceHistoryState(cursor=uuid4(), current_step_id=uuid4(), baseline=baseline)
