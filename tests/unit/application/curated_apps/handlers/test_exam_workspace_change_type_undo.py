"""One server undo after a fallback retype restores kind and source_fallback."""

import random

import pytest

from skriptoteket.application.curated_apps.exam_workspace_history import (
    MoveExamWorkspaceHistoryPositionRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_change_type import (
    ChangeExamWorkspaceItemTypeHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.protocols.exam_workspace_change_type import ChangeExamWorkspaceItemTypeRequest
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _actor,
    _Env,
    _leased_tab,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_history_contract import (
    _handler,
    _undo_handler,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
    make_review,
)


@pytest.mark.asyncio
async def test_one_undo_after_fallback_retype_restores_kind_and_source_fallback() -> None:
    env = _Env()
    actor = _actor()
    fallback = make_free_text_item().model_copy(
        update={
            "review": make_review(
                state=NativeItemReviewState.REVIEW_REQUIRED,
                parse_origin=NativeParseOrigin.SOURCE_FALLBACK,
                confidence=None,
            ).model_copy(update={"reasons": ("Frågan kunde inte konverteras.",)})
        }
    )
    seeded = await env.seed_document(actor=actor, document=make_document(fallback))
    lineage = seeded.summary.lineage_id
    current = await env.get_handler.handle(actor=actor, lineage_id=lineage)

    change_handler = ChangeExamWorkspaceItemTypeHandler(
        reader=env.get_handler, undo_steps=_undo_handler(env), rng=random.Random(1)
    )
    changed = await change_handler.handle(
        actor=actor,
        lineage_id=lineage,
        request=ChangeExamWorkspaceItemTypeRequest(
            tab_id=await _leased_tab(env, actor, lineage),
            item_id=fallback.item_id,
            target_kind=NativeExamItemKind.GAP_FILL,
            expected_revision=current.document.revision,
            expected_cursor=current.history_cursor,
        ),
    )
    assert changed.document.items[0].kind is NativeExamItemKind.GAP_FILL
    assert changed.document.items[0].review.parse_origin is NativeParseOrigin.TEACHER_RETYPED

    history = await _handler(env).history(actor=actor, lineage_id=lineage)
    assert len(history.step_ids) == 1
    undone = await _undo_handler(env).move_to_step(
        actor=actor,
        lineage_id=lineage,
        request=MoveExamWorkspaceHistoryPositionRequest(
            tab_id=await _leased_tab(env, actor, lineage),
            expected_cursor=history.cursor,
            step_id=history.baseline_step_id,
        ),
    )

    restored = undone.document.items[0]
    assert restored.kind is NativeExamItemKind.FREE_TEXT
    assert restored.review == fallback.review
