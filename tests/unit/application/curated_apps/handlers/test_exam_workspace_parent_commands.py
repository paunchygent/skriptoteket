"""Commands use the editor cursor, never the exam-file save boundary."""

from datetime import UTC, datetime
from typing import Literal
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceDocumentResponse,
    ExamWorkspaceDocumentSummary,
)
from skriptoteket.application.curated_apps.exam_workspace_history import (
    ExamWorkspaceHistoryResponse,
    ExamWorkspaceUndoStepResponse,
    StoreExamWorkspaceUndoStepRequest,
)
from skriptoteket.application.curated_apps.exam_workspace_parents import (
    AddExamChildRequest,
    CreateEmptyExamPartRequest,
    CreateExamParentRequest,
    GroupExamItemsRequest,
    MoveExamItemRequest,
    NewParentChild,
    ParentCommandRequest,
    ReorderExamChildrenRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_parents import (
    ExamWorkspaceParentsHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.exam_workspace import GetExamWorkspaceDocumentHandlerProtocol
from skriptoteket.protocols.exam_workspace_history import StoreExamWorkspaceUndoStepHandlerProtocol
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _actor,
    _Env,
    _leased_tab,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_history_contract import (
    _undo_handler,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import plain_body
from tests.unit.domain.curated_apps.exam_workspace.recorded_native_exam_support import (
    parent_over,
    recorded_document,
)

Command = Literal[
    "create", "add", "delete", "reorder", "delete_parent", "cascade", "group", "move", "empty"
]


def document_response(document: NativeExamDocument) -> ExamWorkspaceDocumentResponse:
    return ExamWorkspaceDocumentResponse(
        document=document,
        saved_document=document,
        history_cursor=uuid4(),
        summary=ExamWorkspaceDocumentSummary(
            lineage_id=document.document_id,
            version=document.revision,
            vault_file_id=uuid4(),
            name="English.provdokument.zip",
            title=document.title,
            course_key=None if document.header.course is None else document.header.course.key,
            saved_at=datetime(2026, 10, 17, tzinfo=UTC),
        ),
        notes=("Keep import notes",),
        conversion=None,
    )


async def _invoke(
    handler: ExamWorkspaceParentsHandler,
    command: Command,
    actor: User,
    document: NativeExamDocument,
    expected_cursor: UUID,
    tab_id: UUID,
) -> ExamWorkspaceDocumentResponse:
    child = NewParentChild.model_validate(document.items[0].model_dump())
    if command == "create":
        return await handler.create_parent(
            actor=actor,
            lineage_id=document.document_id,
            request=CreateExamParentRequest(
                expected_cursor=expected_cursor,
                instruction=plain_body("Teacher instruction"),
                child=child,
                position=0,
                tab_id=tab_id,
            ),
        )
    if command == "add":
        return await handler.add_child(
            actor=actor,
            lineage_id=document.document_id,
            parent_id="parent_001",
            request=AddExamChildRequest(
                expected_cursor=expected_cursor, child=child, position=1, tab_id=tab_id
            ),
        )
    if command in ("delete_parent", "cascade"):
        operation = (
            handler.delete_parent
            if command == "delete_parent"
            else handler.delete_parent_with_children
        )
        return await operation(
            actor=actor,
            lineage_id=document.document_id,
            parent_id="parent_001",
            request=ParentCommandRequest(expected_cursor=expected_cursor, tab_id=tab_id),
        )
    if command == "delete":
        return await handler.delete_child(
            actor=actor,
            lineage_id=document.document_id,
            parent_id="parent_001",
            item_id="item_002",
            request=ParentCommandRequest(expected_cursor=expected_cursor, tab_id=tab_id),
        )
    if command == "group":
        return await handler.group_items(
            actor=actor,
            lineage_id=document.document_id,
            request=GroupExamItemsRequest(
                expected_cursor=expected_cursor, item_ids=("item_001", "item_004"), tab_id=tab_id
            ),
        )
    if command == "move":
        return await handler.move_item(
            actor=actor,
            lineage_id=document.document_id,
            request=MoveExamItemRequest(
                expected_cursor=expected_cursor,
                item_id="item_001",
                target_parent_id="parent_001",
                tab_id=tab_id,
            ),
        )
    if command == "empty":
        return await handler.create_empty_part(
            actor=actor,
            lineage_id=document.document_id,
            request=CreateEmptyExamPartRequest(
                expected_cursor=expected_cursor, position=0, tab_id=tab_id
            ),
        )
    return await handler.reorder_children(
        actor=actor,
        lineage_id=document.document_id,
        parent_id="parent_001",
        request=ReorderExamChildrenRequest(
            expected_cursor=expected_cursor, item_ids=("item_003", "item_002"), tab_id=tab_id
        ),
    )


@pytest.mark.parametrize(
    "command",
    ["create", "add", "delete", "reorder", "delete_parent", "cascade", "group", "move", "empty"],
)
async def test_each_command_stores_one_step_and_reopens_the_written_file(
    command: Command,
) -> None:
    actor = make_user()
    document = recorded_document((parent_over("parent_001", "Converted instruction", 2, 3),))
    current = document_response(document)
    reader = AsyncMock(spec=GetExamWorkspaceDocumentHandlerProtocol)
    undo_steps = AsyncMock(spec=StoreExamWorkspaceUndoStepHandlerProtocol)
    reader.handle.return_value = current
    # The seam's normalized document and cursor, not the local draft, are authoritative.
    normalized = document.model_copy(update={"title": "Normalized by editor seam"})
    next_cursor = uuid4()
    undo_steps.handle.return_value = ExamWorkspaceUndoStepResponse(
        document=normalized,
        history=ExamWorkspaceHistoryResponse(
            cursor=next_cursor,
            baseline_step_id=uuid4(),
            step_ids=(next_cursor,),
            position_step_id=next_cursor,
        ),
    )
    reread = current.model_copy(update={"document": normalized, "history_cursor": next_cursor})
    reader.handle.side_effect = [current, reread]
    handler = ExamWorkspaceParentsHandler(reader=reader, undo_steps=undo_steps)
    tab_id = uuid4()

    response = await _invoke(handler, command, actor, document, current.history_cursor, tab_id)

    assert response.document == normalized
    assert response.history_cursor == next_cursor
    assert response.summary == current.summary
    assert response.notes == current.notes
    assert response.conversion == current.conversion
    assert reader.handle.await_count == 2
    reader.handle.assert_awaited_with(actor=actor, lineage_id=document.document_id)
    undo_steps.handle.assert_awaited_once()
    call = undo_steps.handle.call_args.kwargs
    assert call["actor"] == actor
    assert call["lineage_id"] == document.document_id
    request = call["request"]
    assert request.expected_cursor == current.history_cursor
    assert request.tab_id == tab_id
    # Commands always append to the newest undo step; the cursor is not a branch step ID.
    assert request.after_step_id is None
    assert request.document.document_id == document.document_id
    assert request.document.revision == document.revision
    assert request.document.origin == document.origin
    assert request.document != document
    assert response.saved_document == current.saved_document
    NativeExamDocument.model_validate(request.document.model_dump())


@pytest.mark.parametrize(
    "command",
    ["create", "add", "delete", "reorder", "delete_parent", "cascade", "group", "move", "empty"],
)
async def test_each_command_refuses_stale_cursor_even_when_file_revision_matches(
    command: Command,
) -> None:
    actor = make_user()
    document = recorded_document((parent_over("parent_001", "Converted instruction", 2, 3),))
    current = document_response(document)
    reader = AsyncMock(spec=GetExamWorkspaceDocumentHandlerProtocol)
    undo_steps = AsyncMock(spec=StoreExamWorkspaceUndoStepHandlerProtocol)
    reader.handle.return_value = current
    handler = ExamWorkspaceParentsHandler(reader=reader, undo_steps=undo_steps)
    stale_cursor = uuid4()

    with pytest.raises(DomainError) as error:
        await _invoke(handler, command, actor, document, stale_cursor, uuid4())

    assert error.value.code is ErrorCode.CONFLICT
    assert error.value.details == {
        "expected_cursor": str(stale_cursor),
        "current_cursor": str(current.history_cursor),
    }
    undo_steps.handle.assert_not_awaited()


@pytest.mark.parametrize(
    "command",
    ["create", "add", "delete", "reorder", "delete_parent", "cascade", "group", "move", "empty"],
)
async def test_atomic_seam_conflict_is_not_overwritten_or_retried(command: Command) -> None:
    actor = make_user()
    document = recorded_document((parent_over("parent_001", "Converted instruction", 2, 3),))
    current = document_response(document)
    reader = AsyncMock(spec=GetExamWorkspaceDocumentHandlerProtocol)
    undo_steps = AsyncMock(spec=StoreExamWorkspaceUndoStepHandlerProtocol)
    reader.handle.return_value = current
    conflict = DomainError(code=ErrorCode.CONFLICT, message="A concurrent autosave won.")
    undo_steps.handle.side_effect = conflict
    handler = ExamWorkspaceParentsHandler(reader=reader, undo_steps=undo_steps)

    with pytest.raises(DomainError) as error:
        await _invoke(handler, command, actor, document, current.history_cursor, uuid4())

    assert error.value is conflict
    undo_steps.handle.assert_awaited_once()
    reader.handle.assert_awaited_once()


async def test_undo_command_restores_pre_command_document_through_real_editor_seam() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage_id = imported.summary.lineage_id
    undo_steps = _undo_handler(env)
    handler = ExamWorkspaceParentsHandler(reader=env.get_handler, undo_steps=undo_steps)
    created = await _invoke(
        handler,
        "create",
        actor,
        imported.document,
        imported.history_cursor,
        await _leased_tab(env, actor, lineage_id),
    )
    added = await _invoke(
        handler,
        "add",
        actor,
        created.document,
        created.history_cursor,
        await _leased_tab(env, actor, lineage_id),
    )
    assert len(added.document.parents[0].item_ids) == 2
    assert len(created.document.parents[0].item_ids) == 1

    previous = await env.save_handler.history_step(
        actor=actor, lineage_id=lineage_id, step_id=created.history_cursor
    )
    current_head = await env.get_handler.handle(actor=actor, lineage_id=lineage_id)
    assert previous.document == created.document.model_copy(
        update={"revision": current_head.summary.version}
    )
    restored = await undo_steps.handle(
        actor=actor,
        lineage_id=lineage_id,
        request=StoreExamWorkspaceUndoStepRequest(
            document=previous.document,
            expected_cursor=added.history_cursor,
            after_step_id=previous.step_id,
            tab_id=await _leased_tab(env, actor, lineage_id),
        ),
    )
    reopened = await env.get_handler.handle(actor=actor, lineage_id=lineage_id)
    assert restored.document == reopened.document
    assert reopened.document == created.document.model_copy(
        update={"revision": reopened.summary.version}
    )
    assert reopened.history_cursor == restored.history.cursor
    assert added.history_cursor not in restored.history.step_ids
    with pytest.raises(DomainError) as error:
        await env.save_handler.history_step(
            actor=actor, lineage_id=lineage_id, step_id=added.history_cursor
        )
    assert error.value.code is ErrorCode.NOT_FOUND
    saved_file = env.vault_files.files[imported.summary.vault_file_id]
    saved = env.codec.parse(content=await env.store.load(actor=actor, vault_file=saved_file))
    assert saved.document == reopened.document


async def test_group_and_empty_name_the_created_part_and_are_each_one_undo_step() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage_id = imported.summary.lineage_id
    undo_steps = _undo_handler(env)
    handler = ExamWorkspaceParentsHandler(reader=env.get_handler, undo_steps=undo_steps)

    grouped = await handler.group_items(
        actor=actor,
        lineage_id=lineage_id,
        request=GroupExamItemsRequest(
            expected_cursor=imported.history_cursor,
            item_ids=("item_001", "item_003"),
            tab_id=await _leased_tab(env, actor, lineage_id),
        ),
    )
    assert grouped.created_parent_id in {p.parent_id for p in grouped.document.parents}
    assert grouped.history_cursor != imported.history_cursor

    emptied = await handler.create_empty_part(
        actor=actor,
        lineage_id=lineage_id,
        request=CreateEmptyExamPartRequest(
            expected_cursor=grouped.history_cursor,
            position=0,
            tab_id=await _leased_tab(env, actor, lineage_id),
        ),
    )
    assert emptied.created_parent_id != grouped.created_parent_id
    new_part = next(p for p in emptied.document.parents if p.parent_id == emptied.created_parent_id)
    assert new_part.item_ids == ()
    assert emptied.history_cursor != grouped.history_cursor

    history = await env.save_handler.history(actor=actor, lineage_id=lineage_id)
    assert history.step_ids == (grouped.history_cursor, emptied.history_cursor)


async def test_move_is_one_undo_step_restoring_the_exact_previous_document() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage_id = imported.summary.lineage_id
    undo_steps = _undo_handler(env)
    handler = ExamWorkspaceParentsHandler(reader=env.get_handler, undo_steps=undo_steps)

    grouped = await handler.group_items(
        actor=actor,
        lineage_id=lineage_id,
        request=GroupExamItemsRequest(
            expected_cursor=imported.history_cursor,
            item_ids=("item_001", "item_003"),
            tab_id=await _leased_tab(env, actor, lineage_id),
        ),
    )
    moved = await handler.move_item(
        actor=actor,
        lineage_id=lineage_id,
        request=MoveExamItemRequest(
            expected_cursor=grouped.history_cursor,
            item_id="item_005",
            target_parent_id=grouped.created_parent_id,
            tab_id=await _leased_tab(env, actor, lineage_id),
        ),
    )
    assert moved.document.parent_of("item_005") is not None

    previous = await env.save_handler.history_step(
        actor=actor, lineage_id=lineage_id, step_id=grouped.history_cursor
    )
    current_head = await env.get_handler.handle(actor=actor, lineage_id=lineage_id)
    assert previous.document == grouped.document.model_copy(
        update={"revision": current_head.summary.version}
    )
    restored = await undo_steps.handle(
        actor=actor,
        lineage_id=lineage_id,
        request=StoreExamWorkspaceUndoStepRequest(
            document=previous.document,
            expected_cursor=moved.history_cursor,
            after_step_id=previous.step_id,
            tab_id=await _leased_tab(env, actor, lineage_id),
        ),
    )
    reopened = await env.get_handler.handle(actor=actor, lineage_id=lineage_id)
    assert restored.document == reopened.document
    assert reopened.document == grouped.document.model_copy(
        update={"revision": reopened.summary.version}
    )
    assert moved.history_cursor not in restored.history.step_ids
