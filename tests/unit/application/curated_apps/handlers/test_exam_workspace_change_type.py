"""Revision/cursor guards and exactly-one-autosave behavior through application ports."""

import random
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.exam_workspace_history import (
    ExamWorkspaceHistoryResponse,
    ExamWorkspaceUndoStepResponse,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_change_type import (
    ChangeExamWorkspaceItemTypeHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.exam_workspace import GetExamWorkspaceDocumentHandlerProtocol
from skriptoteket.protocols.exam_workspace_change_type import ChangeExamWorkspaceItemTypeRequest
from skriptoteket.protocols.exam_workspace_history import StoreExamWorkspaceUndoStepHandlerProtocol
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.curated_apps.handlers.test_exam_workspace_parent_commands import (
    document_response,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_gap_fill_item,
)


def _ports():
    current = document_response(make_document(make_gap_fill_item()))
    reader = AsyncMock(spec=GetExamWorkspaceDocumentHandlerProtocol)
    reader.handle.return_value = current
    steps = AsyncMock(spec=StoreExamWorkspaceUndoStepHandlerProtocol)
    return current, reader, steps


async def test_one_command_uses_one_atomic_autosave_and_returns_authoritative_result() -> None:
    current, reader, steps = _ports()
    actor = make_user()
    cursor = uuid4()
    # The autosave port can normalize data; the re-read after the store is authoritative.
    normalized = current.document.model_copy(update={"title": "Normalized editor document"})
    steps.handle.return_value = ExamWorkspaceUndoStepResponse(
        document=normalized,
        history=ExamWorkspaceHistoryResponse(
            cursor=cursor, baseline_step_id=uuid4(), step_ids=(cursor,), position_step_id=cursor
        ),
    )
    reread = current.model_copy(update={"document": normalized, "history_cursor": cursor})
    reader.handle.side_effect = [current, reread]
    handler = ChangeExamWorkspaceItemTypeHandler(
        reader=reader, undo_steps=steps, rng=random.Random(1)
    )
    response = await handler.handle(
        actor=actor,
        lineage_id=current.document.document_id,
        request=ChangeExamWorkspaceItemTypeRequest(
            item_id="item_001",
            target_kind=NativeExamItemKind.FREE_TEXT,
            expected_revision=current.document.revision,
            expected_cursor=current.history_cursor,
        ),
    )
    assert reader.handle.await_count == 2
    reader.handle.assert_awaited_with(actor=actor, lineage_id=current.document.document_id)
    steps.handle.assert_awaited_once()
    call = steps.handle.call_args.kwargs
    assert call["actor"] == actor
    assert call["lineage_id"] == current.document.document_id
    request = call["request"]
    assert request.expected_cursor == current.history_cursor
    assert request.after_step_id is None
    assert request.document.revision == current.document.revision
    item = request.document.items[0]
    assert item.kind is NativeExamItemKind.FREE_TEXT
    assert item.points == 2
    assert item.gaps == ()
    assert response.document == normalized
    assert response.history_cursor == cursor
    assert response.saved_document == current.saved_document
    assert response.summary == current.summary
    assert response.notes == current.notes
    assert response.conversion == current.conversion
    assert set(response.dropped_content) == {"gaps", "accepted_values"}


@pytest.mark.parametrize("stale", ["revision", "cursor", "both"])
async def test_stale_precondition_never_stores_a_step(stale: str) -> None:
    current, reader, steps = _ports()
    handler = ChangeExamWorkspaceItemTypeHandler(
        reader=reader, undo_steps=steps, rng=random.Random(1)
    )
    with pytest.raises(DomainError) as error:
        await handler.handle(
            actor=make_user(),
            lineage_id=current.document.document_id,
            request=ChangeExamWorkspaceItemTypeRequest(
                item_id="item_001",
                target_kind=NativeExamItemKind.SINGLE_CHOICE,
                expected_revision=(
                    current.document.revision + 1
                    if stale != "cursor"
                    else current.document.revision
                ),
                expected_cursor=uuid4() if stale != "revision" else current.history_cursor,
            ),
        )
    assert error.value.code is ErrorCode.CONFLICT
    steps.handle.assert_not_awaited()


async def test_concurrent_autosave_conflict_is_not_retried_or_hidden() -> None:
    current, reader, steps = _ports()
    conflict = DomainError(code=ErrorCode.CONFLICT, message="Another editor won")
    steps.handle.side_effect = conflict
    handler = ChangeExamWorkspaceItemTypeHandler(
        reader=reader, undo_steps=steps, rng=random.Random(1)
    )
    with pytest.raises(DomainError) as error:
        await handler.handle(
            actor=make_user(),
            lineage_id=current.document.document_id,
            request=ChangeExamWorkspaceItemTypeRequest(
                item_id="item_001",
                target_kind=NativeExamItemKind.FREE_TEXT,
                expected_revision=current.document.revision,
                expected_cursor=current.history_cursor,
            ),
        )
    assert error.value is conflict
    steps.handle.assert_awaited_once()
    reader.handle.assert_awaited_once()


async def test_matching_precision_error_never_autosaves_or_rounds_points() -> None:
    current, reader, steps = _ports()
    question = current.document.items[0].model_copy(update={"points": 1.234})
    current = current.model_copy(
        update={"document": current.document.model_copy(update={"items": (question,)})}
    )
    reader.handle.return_value = current
    with pytest.raises(DomainError) as error:
        await ChangeExamWorkspaceItemTypeHandler(
            reader=reader, undo_steps=steps, rng=random.Random(1)
        ).handle(
            actor=make_user(),
            lineage_id=current.document.document_id,
            request=ChangeExamWorkspaceItemTypeRequest(
                item_id=question.item_id,
                target_kind=NativeExamItemKind.MATCHING,
                expected_revision=current.document.revision,
                expected_cursor=current.history_cursor,
            ),
        )
    assert error.value.code is ErrorCode.VALIDATION_ERROR
    assert error.value.details["reason"] == "matching_points_precision"
    assert question.points == 1.234
    steps.handle.assert_not_awaited()


async def test_unknown_question_never_stores_a_step() -> None:
    current, reader, steps = _ports()
    with pytest.raises(DomainError) as error:
        await ChangeExamWorkspaceItemTypeHandler(
            reader=reader, undo_steps=steps, rng=random.Random(1)
        ).handle(
            actor=make_user(),
            lineage_id=current.document.document_id,
            request=ChangeExamWorkspaceItemTypeRequest(
                item_id="item_999",
                target_kind=NativeExamItemKind.FREE_TEXT,
                expected_revision=current.document.revision,
                expected_cursor=current.history_cursor,
            ),
        )
    assert error.value.code is ErrorCode.NOT_FOUND
    steps.handle.assert_not_awaited()
