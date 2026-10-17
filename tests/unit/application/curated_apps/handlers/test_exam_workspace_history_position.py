"""The editor's position in its undo history, separate from the concurrency cursor."""

from uuid import UUID, uuid4

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


async def _autosave(env: _Env, actor, lineage, document, after: UUID | None = None) -> UUID:
    cursor = (await _handler(env).history(actor=actor, lineage_id=lineage)).cursor
    response = await _undo_handler(env).handle(
        actor=actor,
        lineage_id=lineage,
        request=StoreExamWorkspaceUndoStepRequest(
            expected_cursor=cursor, document=document, after_step_id=after
        ),
    )
    return response.history.position_step_id


async def _spara(env: _Env, actor, lineage, document, expected_revision: int, position) -> None:
    await _handler(env).handle(
        actor=actor,
        lineage_id=lineage,
        request=SaveExamWorkspaceDocumentRequest(
            expected_revision=expected_revision,
            document=document.model_copy(update={"revision": expected_revision + 1}),
            position_step_id=position,
        ),
    )


async def _titles(env: _Env, actor, lineage, step_ids) -> list[str]:
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
async def test_spara_of_the_autosaved_copy_keeps_the_position_on_its_step() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    edited = imported.document.model_copy(update={"title": "Första"})
    await _autosave(env, actor, lineage, edited)
    second = await _autosave(env, actor, lineage, edited.model_copy(update={"title": "Andra"}))
    before = await _handler(env).history(actor=actor, lineage_id=lineage)

    await _spara(env, actor, lineage, edited.model_copy(update={"title": "Andra"}), 1, second)

    after = await _handler(env).history(actor=actor, lineage_id=lineage)
    # The cursor rotates for concurrency, but it names no step; the position does.
    assert after.cursor != before.cursor
    assert after.cursor not in (after.baseline_step_id, *after.step_ids)
    assert after.step_ids == before.step_ids
    assert after.position_step_id == second


@pytest.mark.asyncio
async def test_spara_keeps_the_teachers_position_among_equal_steps() -> None:
    """A -> B -> A -> C, undo to the first A, Spara: redo must still lead to B."""
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    base = imported.document
    first_a = await _autosave(env, actor, lineage, base.model_copy(update={"title": "A"}))
    for title in ("B", "A", "C"):
        await _autosave(env, actor, lineage, base.model_copy(update={"title": title}))
    before = await _handler(env).history(actor=actor, lineage_id=lineage)

    await _spara(env, actor, lineage, base.model_copy(update={"title": "A"}), 1, first_a)

    after = await _handler(env).history(actor=actor, lineage_id=lineage)
    assert after.step_ids == before.step_ids
    assert after.position_step_id == first_a
    following = after.step_ids[after.step_ids.index(first_a) + 1]
    assert await _titles(env, actor, lineage, [following]) == ["B"]
    reopened = await env.get_handler.handle(actor=actor, lineage_id=lineage)
    assert reopened.document.title == "A"


@pytest.mark.asyncio
async def test_spara_of_an_unmodified_import_keeps_the_position_on_the_baseline() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    await _spara(env, actor, lineage, imported.document, 1, lineage)
    history = await _handler(env).history(actor=actor, lineage_id=lineage)
    assert history.position_step_id == history.baseline_step_id


@pytest.mark.asyncio
async def test_spara_after_a_failed_autosave_retains_the_saved_copy_after_the_position() -> None:
    """The edit's step write never landed; Spara keeps it as the next step at once."""
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    first = await _autosave(
        env, actor, lineage, imported.document.model_copy(update={"title": "Steg"})
    )
    unsaved = imported.document.model_copy(update={"title": "Aldrig autosparad"})

    await _spara(env, actor, lineage, unsaved, 1, first)

    history = await _handler(env).history(actor=actor, lineage_id=lineage)
    assert history.step_ids[:-1] == (first,)
    assert history.position_step_id == history.step_ids[-1]
    assert await _titles(env, actor, lineage, history.step_ids) == ["Steg", "Aldrig autosparad"]
    reopened = await env.get_handler.handle(actor=actor, lineage_id=lineage)
    assert reopened.document.title == "Aldrig autosparad"


@pytest.mark.asyncio
async def test_spara_after_undo_with_an_unstored_edit_branches_after_the_undone_step() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    first = await _autosave(
        env, actor, lineage, imported.document.model_copy(update={"title": "Ett"})
    )
    await _autosave(env, actor, lineage, imported.document.model_copy(update={"title": "Två"}))

    await _spara(
        env, actor, lineage, imported.document.model_copy(update={"title": "Ett, ändrad"}), 1, first
    )

    history = await _handler(env).history(actor=actor, lineage_id=lineage)
    assert await _titles(env, actor, lineage, history.step_ids) == ["Ett", "Ett, ändrad"]
    assert history.position_step_id == history.step_ids[-1]


@pytest.mark.asyncio
async def test_a_command_without_a_position_follows_the_current_step() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    first = await _autosave(
        env, actor, lineage, imported.document.model_copy(update={"title": "Ett"})
    )
    await _autosave(env, actor, lineage, imported.document.model_copy(update={"title": "Två"}))
    await _spara(
        env, actor, lineage, imported.document.model_copy(update={"title": "Ett"}), 1, first
    )

    await _autosave(env, actor, lineage, imported.document.model_copy(update={"title": "Kommando"}))

    history = await _handler(env).history(actor=actor, lineage_id=lineage)
    assert await _titles(env, actor, lineage, history.step_ids) == ["Ett", "Kommando"]


def test_the_position_must_name_a_retained_snapshot() -> None:
    baseline = ExamWorkspaceHistoryStep(step_id=uuid4(), content=b"baseline")
    ExamWorkspaceHistoryState(cursor=uuid4(), current_step_id=baseline.step_id, baseline=baseline)
    with pytest.raises(ValueError):
        ExamWorkspaceHistoryState(cursor=uuid4(), current_step_id=uuid4(), baseline=baseline)
    with pytest.raises(ValueError):
        ExamWorkspaceHistoryState.model_validate(
            {"cursor": uuid4(), "current_step_id": None, "baseline": baseline}
        )
