"""Godta then Angra keeps the printed total the reload reads (TASK-SKRIPT-40-04-14).

Fail-first for the staging defect on main at cf9547fa: the teacher pressed Godta
on the printed-total points line, then Angra. The status read Sparat, but after
a reload the line was gone and the exam read Osparat. On the server,
``document.printed_total`` was null while ``saved_document`` held 70: the old
undo only moved the editor's local position (a ``GET .../history/{step}`` read
in ``useExamWorkspaceHistory.goTo``) and never wrote the Mina filer file, so
the reload read the Godta file while the working copy stood on the older step.

Every stored history step now overwrites the file and ``POST
.../history/position`` moves undo and redo and writes the file too, so the file
a reload reads always holds the step the teacher stands on. These tests pin
that agreement on ``printed_total``: Godta stores the cleared total, Angra
moves back to the printed one, reload reads it, and Gor om restores the
cleared file.
"""

from uuid import UUID

import pytest

from skriptoteket.application.curated_apps.exam_workspace_history import (
    MoveExamWorkspaceHistoryPositionRequest,
    StoreExamWorkspaceUndoStepRequest,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
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

_PRINTED_TOTAL = 70


def _with_printed_total(document: NativeExamDocument, printed: float | None) -> NativeExamDocument:
    """One level's printed total set or cleared, like the points line's Godta."""
    return document.model_copy(
        update={"header": document.header.model_copy(update={"printed_total": printed})}
    )


async def _seed_with_printed_total(env: _Env) -> tuple[User, UUID]:
    """An exam whose file prints 70, stored as one undo step past the import baseline."""
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    cursor = (await _handler(env).history(actor=actor, lineage_id=lineage)).cursor
    await _undo_handler(env).handle(
        actor=actor,
        lineage_id=lineage,
        request=StoreExamWorkspaceUndoStepRequest(
            tab_id=await _leased_tab(env, actor, lineage),
            expected_cursor=cursor,
            document=_with_printed_total(imported.document, _PRINTED_TOTAL),
        ),
    )
    return actor, lineage


async def _store_cleared(env: _Env, actor: User, lineage: UUID) -> UUID:
    """Godta: clear the exam's printed total as its own undo step; return its step id."""
    history = await _handler(env).history(actor=actor, lineage_id=lineage)
    cleared = _with_printed_total(
        (
            await _handler(env).history_step(
                actor=actor, lineage_id=lineage, step_id=history.step_ids[-1]
            )
        ).document,
        None,
    )
    stored = await _undo_handler(env).handle(
        actor=actor,
        lineage_id=lineage,
        request=StoreExamWorkspaceUndoStepRequest(
            tab_id=await _leased_tab(env, actor, lineage),
            expected_cursor=history.cursor,
            document=cleared,
        ),
    )
    return stored.history.position_step_id


async def _move(env: _Env, actor: User, lineage: UUID, step_id: UUID) -> NativeExamDocument:
    """Angra or Gor om to a retained step; return the working copy the move confirms."""
    history = await _handler(env).history(actor=actor, lineage_id=lineage)
    moved = await _undo_handler(env).move_to_step(
        actor=actor,
        lineage_id=lineage,
        request=MoveExamWorkspaceHistoryPositionRequest(
            tab_id=await _leased_tab(env, actor, lineage),
            expected_cursor=history.cursor,
            step_id=step_id,
        ),
    )
    return moved.document


@pytest.mark.asyncio
async def test_godta_then_angra_restores_the_printed_total_the_reload_reads() -> None:
    env = _Env()
    actor, lineage = await _seed_with_printed_total(env)
    before = await _handler(env).history(actor=actor, lineage_id=lineage)
    printed_step = before.step_ids[-1]

    cleared_step = await _store_cleared(env, actor, lineage)
    reopened = await env.get_handler.handle(actor=actor, lineage_id=lineage)
    assert reopened.document.header.printed_total is None
    assert reopened.saved_document.header.printed_total is None

    moved = await _move(env, actor, lineage, printed_step)

    assert moved.header.printed_total == _PRINTED_TOTAL
    reopened = await env.get_handler.handle(actor=actor, lineage_id=lineage)
    assert reopened.document.header.printed_total == _PRINTED_TOTAL
    assert reopened.saved_document.header.printed_total == _PRINTED_TOTAL
    assert reopened.document.header.printed_total == reopened.saved_document.header.printed_total
    current = await _handler(env).history(actor=actor, lineage_id=lineage)
    assert current.position_step_id == printed_step
    assert current.step_ids == (*before.step_ids, cleared_step)


@pytest.mark.asyncio
async def test_gor_om_after_angra_clears_the_printed_total_in_the_file_again() -> None:
    env = _Env()
    actor, lineage = await _seed_with_printed_total(env)
    before = await _handler(env).history(actor=actor, lineage_id=lineage)
    printed_step = before.step_ids[-1]

    cleared_step = await _store_cleared(env, actor, lineage)
    undone = await _move(env, actor, lineage, printed_step)
    assert undone.header.printed_total == _PRINTED_TOTAL

    redone = await _move(env, actor, lineage, cleared_step)

    assert redone.header.printed_total is None
    reopened = await env.get_handler.handle(actor=actor, lineage_id=lineage)
    assert reopened.document.header.printed_total is None
    assert reopened.saved_document.header.printed_total is None
