"""R2: redo survives a reload (backend regression)."""

from uuid import UUID

import pytest

from skriptoteket.application.curated_apps.exam_workspace_history import (
    MoveExamWorkspaceHistoryPositionRequest,
    StoreExamWorkspaceUndoStepRequest,
)
from skriptoteket.domain.identity.models import User
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _actor,
    _Env,
    _leased_tab,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_history_contract import (
    _handler,
    _undo_handler,
)


async def _store_title(env: _Env, actor: User, lineage: UUID, title: str) -> None:
    cursor = (await _handler(env).history(actor=actor, lineage_id=lineage)).cursor
    opened = await env.get_handler.handle(actor=actor, lineage_id=lineage)
    await _undo_handler(env).handle(
        actor=actor,
        lineage_id=lineage,
        request=StoreExamWorkspaceUndoStepRequest(
            tab_id=await _leased_tab(env, actor, lineage),
            expected_cursor=cursor,
            document=opened.document.model_copy(update={"title": title}),
        ),
    )


async def _move(env: _Env, actor: User, lineage: UUID, step: UUID):
    cursor = (await _handler(env).history(actor=actor, lineage_id=lineage)).cursor
    return await _undo_handler(env).move_to_step(
        actor=actor,
        lineage_id=lineage,
        request=MoveExamWorkspaceHistoryPositionRequest(
            expected_cursor=cursor,
            step_id=step,
            tab_id=await _leased_tab(env, actor, lineage),
        ),
    )


@pytest.mark.asyncio
async def test_undo_keeps_redo_for_a_reload() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    await _store_title(env, actor, lineage, "Ett")
    await _store_title(env, actor, lineage, "Två")
    before = await _handler(env).history(actor=actor, lineage_id=lineage)
    moved = await _move(env, actor, lineage, before.step_ids[0])
    assert moved.history.position_step_id == before.step_ids[0]
    assert moved.history.step_ids == before.step_ids
    reopened = await env.get_handler.handle(actor=actor, lineage_id=lineage)
    assert reopened.document.title == "Ett"
    reloaded = await _handler(env).history(actor=actor, lineage_id=lineage)
    assert reloaded.position_step_id == before.step_ids[0]
    assert reloaded.step_ids == before.step_ids
    assert reopened.history_cursor == reloaded.cursor


@pytest.mark.asyncio
async def test_redo_to_newest_leaves_no_redo_after_reload() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    await _store_title(env, actor, lineage, "Ett")
    await _store_title(env, actor, lineage, "Två")
    before = await _handler(env).history(actor=actor, lineage_id=lineage)
    first, second = before.step_ids
    await _move(env, actor, lineage, first)
    redone = await _move(env, actor, lineage, second)
    assert redone.history.position_step_id == second
    reopened = await env.get_handler.handle(actor=actor, lineage_id=lineage)
    assert reopened.document.title == "Två"
    reloaded = await _handler(env).history(actor=actor, lineage_id=lineage)
    assert reloaded.position_step_id == second
