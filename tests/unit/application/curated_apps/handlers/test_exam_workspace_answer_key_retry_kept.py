"""The saved answer-key retry never moves backwards on a head write.

Purpose:
    Prove the retry kept per question survives the server-side undo and save
    paths (TASK-SKRIPT-40-04-26 D4): a position move back to a step that says
    offered writes and returns used, a save of an offered document over a
    used head keeps used, and a new question or a none-to-offered question
    saves as sent.
"""

from uuid import UUID

import pytest

from skriptoteket.application.curated_apps.exam_workspace_history import (
    ExamWorkspaceUndoStepResponse,
    MoveExamWorkspaceHistoryPositionRequest,
    StoreExamWorkspaceUndoStepRequest,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyRetry,
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
from tests.unit.application.curated_apps.handlers.workspace_suggestion_handler_support import (
    suggestion_item,
)

_ITEM_ID = "item_001"


def _with_retry(
    document: NativeExamDocument,
    retry: NativeAnswerKeyRetry,
    *,
    item_id: str = _ITEM_ID,
) -> NativeExamDocument:
    return document.model_copy(
        update={
            "items": tuple(
                item.model_copy(update={"answer_key_retry": retry})
                if item.item_id == item_id
                else item
                for item in document.items
            )
        }
    )


def _retry(document: NativeExamDocument, *, item_id: str = _ITEM_ID) -> NativeAnswerKeyRetry:
    return document.item_by_id(item_id).answer_key_retry


async def _cursor(env: _Env, actor: User, lineage: UUID) -> UUID:
    return (await _handler(env).history(actor=actor, lineage_id=lineage)).cursor


async def _store_step(
    env: _Env, actor: User, lineage: UUID, document: NativeExamDocument
) -> ExamWorkspaceUndoStepResponse:
    return await _undo_handler(env).handle(
        actor=actor,
        lineage_id=lineage,
        request=StoreExamWorkspaceUndoStepRequest(
            tab_id=await _leased_tab(env, actor, lineage),
            expected_cursor=await _cursor(env, actor, lineage),
            document=document,
        ),
    )


async def _move(
    env: _Env, actor: User, lineage: UUID, step_id: UUID
) -> ExamWorkspaceUndoStepResponse:
    return await _undo_handler(env).move_to_step(
        actor=actor,
        lineage_id=lineage,
        request=MoveExamWorkspaceHistoryPositionRequest(
            tab_id=await _leased_tab(env, actor, lineage),
            expected_cursor=await _cursor(env, actor, lineage),
            step_id=step_id,
        ),
    )


async def _saved_head(env: _Env, actor: User, lineage: UUID) -> NativeExamDocument:
    head = await env.vault_files.get_document_head(user_id=actor.id, document_lineage_id=lineage)
    assert head is not None
    return env.codec.parse(content=await env.store.load(actor=actor, vault_file=head)).document


async def _used_head_with_offered_step(env: _Env, actor: User) -> tuple[UUID, UUID]:
    """Seed an exam whose head is used and whose earlier step still says offered."""
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    base = imported.document
    offered_step = (
        await _store_step(env, actor, lineage, _with_retry(base, NativeAnswerKeyRetry.OFFERED))
    ).history.position_step_id
    await _store_step(env, actor, lineage, _with_retry(base, NativeAnswerKeyRetry.USED))
    assert _retry(await _saved_head(env, actor, lineage)) is NativeAnswerKeyRetry.USED
    return lineage, offered_step


@pytest.mark.asyncio
async def test_a_move_back_to_an_offered_step_writes_the_saved_used_retry() -> None:
    env = _Env()
    actor = _actor()
    lineage, offered_step = await _used_head_with_offered_step(env, actor)

    response = await _move(env, actor, lineage, offered_step)

    assert _retry(response.document) is NativeAnswerKeyRetry.USED
    assert _retry(await _saved_head(env, actor, lineage)) is NativeAnswerKeyRetry.USED


@pytest.mark.asyncio
async def test_reopening_after_that_move_reads_the_saved_used_retry() -> None:
    env = _Env()
    actor = _actor()
    lineage, offered_step = await _used_head_with_offered_step(env, actor)
    await _move(env, actor, lineage, offered_step)

    reopened = await env.get_handler.handle(actor=actor, lineage_id=lineage)

    assert _retry(reopened.document) is NativeAnswerKeyRetry.USED


@pytest.mark.asyncio
async def test_saving_an_offered_document_over_a_used_head_keeps_used() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    base = imported.document
    await _store_step(env, actor, lineage, _with_retry(base, NativeAnswerKeyRetry.USED))

    response = await _store_step(
        env, actor, lineage, _with_retry(base, NativeAnswerKeyRetry.OFFERED)
    )

    assert _retry(response.document) is NativeAnswerKeyRetry.USED
    assert _retry(await _saved_head(env, actor, lineage)) is NativeAnswerKeyRetry.USED
    history = await _handler(env).history(actor=actor, lineage_id=lineage)
    stored = await _handler(env).history_step(
        actor=actor, lineage_id=lineage, step_id=history.position_step_id
    )
    assert _retry(stored.document) is NativeAnswerKeyRetry.USED


@pytest.mark.asyncio
async def test_a_new_question_and_a_none_to_offered_question_save_as_sent() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    base = imported.document
    offered = _with_retry(base, NativeAnswerKeyRetry.OFFERED)
    sent = offered.model_copy(
        update={
            "items": (
                *offered.items,
                suggestion_item(item_id="item_009", sequence=9, retry=NativeAnswerKeyRetry.OFFERED),
            )
        }
    )

    response = await _store_step(env, actor, lineage, sent)

    assert _retry(response.document) is NativeAnswerKeyRetry.OFFERED
    assert _retry(response.document, item_id="item_009") is NativeAnswerKeyRetry.OFFERED
    saved = await _saved_head(env, actor, lineage)
    assert _retry(saved) is NativeAnswerKeyRetry.OFFERED
    assert _retry(saved, item_id="item_009") is NativeAnswerKeyRetry.OFFERED
