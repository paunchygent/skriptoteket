"""The print preview renders the persisted working snapshot the editor stands on (W5, R3).

A draft edit autosaves as a history undo step and does not move the saved file
revision, so the preview must read the history snapshot behind ``current_step_id``
and be guarded by both the saved head revision and the history cursor. These tests
drive the real preview handler over the in-memory store and assert on the print
HTML handed to a recording renderer, never on a simulation.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.exam_workspace_history import (
    ExamWorkspaceUndoStepResponse,
    StoreExamWorkspaceUndoStepRequest,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _actor,
    _Env,
    _leased_tab,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_history_contract import (
    _undo_handler,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_print_preview import (
    _document_with_asset,
    _FakePrintRenderer,
    _preview_handler,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
)

_WRITING_LINE = '<div class="writing-line"></div>'
_IMPORT_WRITING_LINES = 8


def _writing_lines(document: NativeExamDocument, count: int) -> NativeExamDocument:
    item = document.items[0].model_copy(update={"writing_lines": count})
    return document.model_copy(update={"items": (item, *document.items[1:])})


async def _store_draft_step(
    env: _Env,
    *,
    lineage_id: UUID,
    actor: User,
    cursor: UUID,
    document: NativeExamDocument,
) -> ExamWorkspaceUndoStepResponse:
    return await _undo_handler(env).handle(
        actor=actor,
        lineage_id=lineage_id,
        request=StoreExamWorkspaceUndoStepRequest(
            expected_cursor=cursor,
            document=document,
            tab_id=await _leased_tab(env, actor, lineage_id),
        ),
    )


@pytest.mark.asyncio
async def test_preview_renders_the_requested_baseline_step_not_the_current_step() -> None:
    """Undo navigation names the baseline; the preview must render those 8 lines (R3)."""
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor, document=make_document(make_free_text_item()))
    lineage = imported.summary.lineage_id
    step = await _store_draft_step(
        env,
        lineage_id=lineage,
        actor=actor,
        cursor=imported.history_cursor,
        document=_writing_lines(imported.document, 9),
    )
    assert step.history.position_step_id != imported.history_cursor
    renderer = _FakePrintRenderer()

    response = await _preview_handler(env, print_renderer=renderer).handle(
        actor=actor,
        lineage_id=lineage,
        expected_revision=2,
        expected_cursor=step.history.cursor,
        step_id=imported.history_cursor,
    )

    assert response.status == "ready"
    assert len(renderer.html_by_call) == 1
    assert renderer.html_by_call[0].count(_WRITING_LINE) == _IMPORT_WRITING_LINES


@pytest.mark.asyncio
async def test_preview_renders_the_requested_stored_step() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor, document=make_document(make_free_text_item()))
    lineage = imported.summary.lineage_id
    step = await _store_draft_step(
        env,
        lineage_id=lineage,
        actor=actor,
        cursor=imported.history_cursor,
        document=_writing_lines(imported.document, 9),
    )
    renderer = _FakePrintRenderer()

    response = await _preview_handler(env, print_renderer=renderer).handle(
        actor=actor,
        lineage_id=lineage,
        expected_revision=2,
        expected_cursor=step.history.cursor,
        step_id=step.history.position_step_id,
    )

    assert response.status == "ready"
    assert renderer.html_by_call[0].count(_WRITING_LINE) == 9


@pytest.mark.asyncio
async def test_preview_with_an_unretained_step_id_conflicts() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor, document=make_document(make_free_text_item()))
    lineage = imported.summary.lineage_id
    step = await _store_draft_step(
        env,
        lineage_id=lineage,
        actor=actor,
        cursor=imported.history_cursor,
        document=_writing_lines(imported.document, 9),
    )
    renderer = _FakePrintRenderer()
    missing = uuid4()

    with pytest.raises(DomainError) as error:
        await _preview_handler(env, print_renderer=renderer).handle(
            actor=actor,
            lineage_id=lineage,
            expected_revision=2,
            expected_cursor=step.history.cursor,
            step_id=missing,
        )

    assert error.value.code is ErrorCode.CONFLICT
    assert error.value.details == {"step_id": str(missing)}
    assert renderer.html_by_call == []


@pytest.mark.asyncio
async def test_preview_renders_the_requested_step_and_the_file_holds_it() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor, document=make_document(make_free_text_item()))
    lineage = imported.summary.lineage_id
    assert imported.document.items[0].writing_lines == _IMPORT_WRITING_LINES

    step = await _store_draft_step(
        env,
        lineage_id=lineage,
        actor=actor,
        cursor=imported.history_cursor,
        document=_writing_lines(imported.document, 9),
    )
    renderer = _FakePrintRenderer()

    response = await _preview_handler(env, print_renderer=renderer).handle(
        actor=actor,
        lineage_id=lineage,
        expected_revision=2,
        expected_cursor=step.history.cursor,
        step_id=step.history.position_step_id,
    )

    assert response.status == "ready"
    assert response.revision == 2
    assert len(renderer.html_by_call) == 1
    assert renderer.html_by_call[0].count(_WRITING_LINE) == 9
    # Every stored step overwrites the saved file, so it holds the 9-line draft.
    saved_file = env.vault_files.files[imported.summary.vault_file_id]
    saved = env.codec.parse(content=await env.store.load(actor=actor, vault_file=saved_file))
    assert saved.document.items[0].writing_lines == 9


@pytest.mark.asyncio
async def test_preview_follows_the_editor_after_undo_rotates_the_cursor() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor, document=make_document(make_free_text_item()))
    lineage = imported.summary.lineage_id

    first = await _store_draft_step(
        env,
        lineage_id=lineage,
        actor=actor,
        cursor=imported.history_cursor,
        document=_writing_lines(imported.document, 9),
    )
    second = await _store_draft_step(
        env,
        lineage_id=lineage,
        actor=actor,
        cursor=first.history.cursor,
        document=_writing_lines(imported.document, 10),
    )
    # Undo moves the editor back to the 9-line snapshot as a new step after it.
    restored = await _undo_handler(env).handle(
        actor=actor,
        lineage_id=lineage,
        request=StoreExamWorkspaceUndoStepRequest(
            tab_id=await _leased_tab(env, actor, lineage),
            expected_cursor=second.history.cursor,
            document=_writing_lines(imported.document, 9),
            after_step_id=first.history.position_step_id,
        ),
    )
    renderer = _FakePrintRenderer()

    response = await _preview_handler(env, print_renderer=renderer).handle(
        actor=actor,
        lineage_id=lineage,
        expected_revision=4,
        expected_cursor=restored.history.cursor,
        step_id=restored.history.position_step_id,
    )

    assert response.status == "ready"
    assert renderer.html_by_call[0].count(_WRITING_LINE) == 9


@pytest.mark.asyncio
async def test_stale_expected_cursor_conflicts_and_never_renders() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor, document=make_document(make_free_text_item()))
    lineage = imported.summary.lineage_id
    step = await _store_draft_step(
        env,
        lineage_id=lineage,
        actor=actor,
        cursor=imported.history_cursor,
        document=_writing_lines(imported.document, 9),
    )
    renderer = _FakePrintRenderer()
    stale_cursor = imported.history_cursor

    with pytest.raises(DomainError) as error:
        await _preview_handler(env, print_renderer=renderer).handle(
            actor=actor,
            lineage_id=lineage,
            expected_revision=2,
            expected_cursor=stale_cursor,
            step_id=imported.history_cursor,
        )

    assert error.value.code is ErrorCode.CONFLICT
    assert error.value.details == {
        "expected_cursor": str(stale_cursor),
        "current_cursor": str(step.history.cursor),
    }
    assert renderer.html_by_call == []


@pytest.mark.asyncio
async def test_stale_expected_revision_conflicts_with_a_fresh_cursor_and_never_renders() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor, document=make_document(make_free_text_item()))
    lineage = imported.summary.lineage_id
    step = await _store_draft_step(
        env,
        lineage_id=lineage,
        actor=actor,
        cursor=imported.history_cursor,
        document=_writing_lines(imported.document, 9),
    )
    renderer = _FakePrintRenderer()

    with pytest.raises(DomainError) as error:
        await _preview_handler(env, print_renderer=renderer).handle(
            actor=actor,
            lineage_id=lineage,
            expected_revision=1,
            expected_cursor=step.history.cursor,
            step_id=step.history.position_step_id,
        )

    assert error.value.code is ErrorCode.CONFLICT
    assert error.value.details == {"expected_revision": 1, "current_revision": 2}
    assert renderer.html_by_call == []


@pytest.mark.asyncio
async def test_a_picture_referenced_in_the_draft_step_renders_ready() -> None:
    env = _Env()
    actor = _actor()
    document, payload, asset_id = _document_with_asset()
    await env.store.save(
        actor=actor,
        file_id=env.ids.new_uuid(),
        name="prov.provdokument.zip",
        content=env.codec.build(
            content=ExamWorkspaceContainerContent(
                document=document, assets_by_id={asset_id: payload}, notes=()
            )
        ),
        lineage_id=document.document_id,
        version=1,
    )
    lineage = document.document_id
    head_history = await env.store.get_history(actor=actor, lineage_id=lineage)
    step = await _store_draft_step(
        env,
        lineage_id=lineage,
        actor=actor,
        cursor=head_history.cursor,
        document=_writing_lines(document, 9),
    )
    renderer = _FakePrintRenderer()

    response = await _preview_handler(env, print_renderer=renderer).handle(
        actor=actor,
        lineage_id=lineage,
        expected_revision=2,
        expected_cursor=step.history.cursor,
        step_id=step.history.position_step_id,
    )

    assert response.status == "ready"
    assert renderer.html_by_call
    assert renderer.html_by_call[0].count(_WRITING_LINE) == 9


@pytest.mark.asyncio
async def test_a_preview_writes_neither_the_saved_file_nor_history() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor, document=make_document(make_free_text_item()))
    lineage = imported.summary.lineage_id
    step = await _store_draft_step(
        env,
        lineage_id=lineage,
        actor=actor,
        cursor=imported.history_cursor,
        document=_writing_lines(imported.document, 9),
    )
    saved_before = env.vault_files.files[imported.summary.vault_file_id]
    content_before = await env.store.load(actor=actor, vault_file=saved_before)
    history_before = await env.store.get_history(actor=actor, lineage_id=lineage)

    response = await _preview_handler(env).handle(
        actor=actor,
        lineage_id=lineage,
        expected_revision=2,
        expected_cursor=step.history.cursor,
        step_id=step.history.position_step_id,
    )

    assert response.status == "ready"
    assert env.vault_files.files[imported.summary.vault_file_id] == saved_before
    assert await env.store.load(actor=actor, vault_file=saved_before) == content_before
    assert await env.store.get_history(actor=actor, lineage_id=lineage) == history_before
    assert len(env.vault_files.files) == 1
