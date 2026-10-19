"""The editor's position in its undo history, separate from the concurrency cursor."""

from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.exam_workspace_history import (
    ExamWorkspaceHistoryState,
    ExamWorkspaceHistoryStep,
    MoveExamWorkspaceHistoryPositionRequest,
    StoreExamWorkspaceUndoStepRequest,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _actor,
    _Env,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_history_contract import (
    _handler,
    _undo_handler,
)


async def _store_step(
    env: _Env, actor: User, lineage: UUID, document: NativeExamDocument, after: UUID | None = None
) -> UUID:
    cursor = (await _handler(env).history(actor=actor, lineage_id=lineage)).cursor
    response = await _undo_handler(env).handle(
        actor=actor,
        lineage_id=lineage,
        request=StoreExamWorkspaceUndoStepRequest(
            expected_cursor=cursor, document=document, after_step_id=after
        ),
    )
    return response.history.position_step_id


async def _move(env: _Env, actor: User, lineage: UUID, step: UUID) -> UUID:
    cursor = (await _handler(env).history(actor=actor, lineage_id=lineage)).cursor
    response = await _undo_handler(env).move_to_step(
        actor=actor,
        lineage_id=lineage,
        request=MoveExamWorkspaceHistoryPositionRequest(expected_cursor=cursor, step_id=step),
    )
    return response.history.position_step_id


async def _titles(env: _Env, actor: User, lineage: UUID, step_ids: tuple[UUID, ...]) -> list[str]:
    return [
        (
            await _handler(env).history_step(actor=actor, lineage_id=lineage, step_id=step)
        ).document.title
        for step in step_ids
    ]


@pytest.mark.asyncio
async def test_a_fresh_import_stands_on_its_baseline() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    history = await _handler(env).history(actor=actor, lineage_id=imported.summary.lineage_id)
    assert history.step_ids == ()
    assert history.position_step_id == history.baseline_step_id


@pytest.mark.asyncio
async def test_each_stored_step_moves_the_position_to_itself() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    first = await _store_step(
        env, actor, lineage, imported.document.model_copy(update={"title": "Första"})
    )
    second = await _store_step(
        env, actor, lineage, imported.document.model_copy(update={"title": "Andra"})
    )
    history = await _handler(env).history(actor=actor, lineage_id=lineage)

    # The cursor rotates for concurrency, but it names the newest step; the position does too.
    assert history.step_ids == (first, second)
    assert history.cursor == second
    assert history.position_step_id == second


@pytest.mark.asyncio
async def test_a_store_after_a_move_drops_the_redo_steps() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    base = imported.document
    first = await _store_step(env, actor, lineage, base.model_copy(update={"title": "Ett"}))
    await _store_step(env, actor, lineage, base.model_copy(update={"title": "Två"}))
    await _move(env, actor, lineage, first)

    position = await _store_step(env, actor, lineage, base.model_copy(update={"title": "Ny gren"}))

    history = await _handler(env).history(actor=actor, lineage_id=lineage)
    assert history.step_ids == (first, position)
    assert history.position_step_id == position
    assert await _titles(env, actor, lineage, history.step_ids) == ["Ett", "Ny gren"]
    reopened = await env.get_handler.handle(actor=actor, lineage_id=lineage)
    assert reopened.document.title == "Ny gren"


@pytest.mark.asyncio
async def test_a_move_stands_on_the_named_snapshot_without_storing() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    first = await _store_step(
        env, actor, lineage, imported.document.model_copy(update={"title": "Ett"})
    )
    await _store_step(env, actor, lineage, imported.document.model_copy(update={"title": "Två"}))
    before = await _handler(env).history(actor=actor, lineage_id=lineage)

    await _move(env, actor, lineage, first)

    after = await _handler(env).history(actor=actor, lineage_id=lineage)
    assert after.step_ids == before.step_ids
    assert after.position_step_id == first
    assert after.cursor != before.cursor
    reopened = await env.get_handler.handle(actor=actor, lineage_id=lineage)
    assert reopened.document.title == "Ett"


@pytest.mark.asyncio
async def test_a_stale_move_is_a_conflict_and_keeps_the_file() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    await _store_step(env, actor, lineage, imported.document.model_copy(update={"title": "Nyare"}))
    opened = await _handler(env).history(actor=actor, lineage_id=imported.summary.lineage_id)
    await _store_step(env, actor, lineage, imported.document.model_copy(update={"title": "Nyast"}))
    saved_before = (await env.get_handler.handle(actor=actor, lineage_id=lineage)).document.title

    with pytest.raises(DomainError) as error:
        await _undo_handler(env).move_to_step(
            actor=actor,
            lineage_id=lineage,
            request=MoveExamWorkspaceHistoryPositionRequest(
                expected_cursor=opened.cursor, step_id=opened.step_ids[0]
            ),
        )

    assert error.value.code is ErrorCode.CONFLICT
    reopened = await env.get_handler.handle(actor=actor, lineage_id=lineage)
    assert reopened.document.title == saved_before


def test_the_position_must_name_a_retained_snapshot() -> None:
    baseline = ExamWorkspaceHistoryStep(step_id=uuid4(), content=b"baseline")
    ExamWorkspaceHistoryState(cursor=uuid4(), current_step_id=baseline.step_id, baseline=baseline)
    with pytest.raises(ValueError):
        ExamWorkspaceHistoryState(cursor=uuid4(), current_step_id=uuid4(), baseline=baseline)
    with pytest.raises(ValueError):
        ExamWorkspaceHistoryState.model_validate(
            {"cursor": uuid4(), "current_step_id": None, "baseline": baseline}
        )
