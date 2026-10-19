"""One save model: every stored step also overwrites the exam file, and moves do too."""

import hashlib
import time
from uuid import UUID, uuid4

import pytest
from fastapi.routing import APIRoute

from skriptoteket.application.curated_apps.exam_workspace_history import (
    MAX_RETAINED_UNDO_STEPS,
    ExamWorkspaceUndoStepResponse,
    MoveExamWorkspaceHistoryPositionRequest,
    StoreExamWorkspaceUndoStepRequest,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import ExamWorkspaceContainerContent
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import NativeAssetSegment
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault import VaultFile
from skriptoteket.web.api.v1 import apps_conversion_hub_exam_workspace as documents_api
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _actor,
    _Env,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_history_contract import (
    _handler,
    _undo_handler,
)


async def _store(
    env: _Env, actor: User, lineage: UUID, document: NativeExamDocument, after: UUID | None = None
) -> ExamWorkspaceUndoStepResponse:
    cursor = (await _handler(env).history(actor=actor, lineage_id=lineage)).cursor
    return await _undo_handler(env).handle(
        actor=actor,
        lineage_id=lineage,
        request=StoreExamWorkspaceUndoStepRequest(
            expected_cursor=cursor, document=document, after_step_id=after
        ),
    )


def _head_file(env: _Env, lineage: UUID) -> VaultFile:
    return next(
        file
        for file in env.vault_files.files.values()
        if file.document_lineage_id == lineage and file.export_format is None
    )


async def _saved_document(env: _Env, actor: User, lineage: UUID) -> NativeExamDocument:
    head = _head_file(env, lineage)
    return env.codec.parse(content=await env.store.load(actor=actor, vault_file=head)).document


@pytest.mark.asyncio
async def test_stored_step_overwrites_the_exam_file_with_the_next_version() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id

    stored = await _store(
        env, actor, lineage, imported.document.model_copy(update={"title": "Autosparad text"})
    )

    assert stored.document.revision == imported.summary.version + 1
    assert stored.history.position_step_id == stored.history.cursor
    saved = await _saved_document(env, actor, lineage)
    assert saved.title == "Autosparad text"
    assert saved.revision == imported.summary.version + 1
    row = next(
        file
        for file in env.vault_files.files.values()
        if file.document_lineage_id == lineage and file.export_format is None
    )
    assert row.document_version == imported.summary.version + 1
    reopened = await env.get_handler.handle(actor=actor, lineage_id=lineage)
    assert reopened.document.title == "Autosparad text"
    assert reopened.summary.version == imported.summary.version + 1
    assert reopened.history_cursor == stored.history.cursor


@pytest.mark.asyncio
async def test_each_stored_step_increases_the_file_version_by_one() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    for index, title in enumerate(("Ett", "Två", "Tre"), start=1):
        stored = await _store(
            env, actor, lineage, imported.document.model_copy(update={"title": title})
        )
        assert stored.document.revision == imported.summary.version + index
        assert (await _saved_document(env, actor, lineage)).revision == (
            imported.summary.version + index
        )
    reopened = await env.get_handler.handle(actor=actor, lineage_id=lineage)
    assert reopened.summary.version == imported.summary.version + 3


@pytest.mark.asyncio
async def test_position_move_writes_the_step_document_without_a_new_step() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    for title in ("Första", "Andra", "Tredje"):
        await _store(env, actor, lineage, imported.document.model_copy(update={"title": title}))
    before = await _handler(env).history(actor=actor, lineage_id=lineage)
    first = before.step_ids[0]
    version_before = (await env.get_handler.handle(actor=actor, lineage_id=lineage)).summary.version

    moved = await _undo_handler(env).move_to_step(
        actor=actor,
        lineage_id=lineage,
        request=MoveExamWorkspaceHistoryPositionRequest(
            expected_cursor=before.cursor, step_id=first
        ),
    )

    after = await _handler(env).history(actor=actor, lineage_id=lineage)
    assert after.step_ids == before.step_ids
    assert after.position_step_id == first
    assert after.cursor != before.cursor
    assert after.cursor == moved.history.cursor
    assert moved.document.title == "Första"
    assert moved.document.revision == version_before + 1
    assert (await _saved_document(env, actor, lineage)).title == "Första"
    reopened = await env.get_handler.handle(actor=actor, lineage_id=lineage)
    assert reopened.document.title == "Första"
    assert reopened.summary.version == version_before + 1


@pytest.mark.asyncio
async def test_position_move_to_the_baseline_restores_the_import() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    await _store(env, actor, lineage, imported.document.model_copy(update={"title": "Ändrad"}))
    before = await _handler(env).history(actor=actor, lineage_id=lineage)

    moved = await _undo_handler(env).move_to_step(
        actor=actor,
        lineage_id=lineage,
        request=MoveExamWorkspaceHistoryPositionRequest(
            expected_cursor=before.cursor, step_id=before.baseline_step_id
        ),
    )

    after = await _handler(env).history(actor=actor, lineage_id=lineage)
    assert after.position_step_id == before.baseline_step_id
    assert after.step_ids == before.step_ids
    assert moved.document.title == imported.document.title
    assert (await _saved_document(env, actor, lineage)).title == imported.document.title


@pytest.mark.asyncio
async def test_position_move_to_an_unknown_step_is_not_found_and_keeps_the_file() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    await _store(env, actor, lineage, imported.document.model_copy(update={"title": "Ändrad"}))
    before = await _handler(env).history(actor=actor, lineage_id=lineage)
    saved_before = await _saved_document(env, actor, lineage)

    with pytest.raises(DomainError) as error:
        await _undo_handler(env).move_to_step(
            actor=actor,
            lineage_id=lineage,
            request=MoveExamWorkspaceHistoryPositionRequest(
                expected_cursor=before.cursor, step_id=uuid4()
            ),
        )

    assert error.value.code is ErrorCode.NOT_FOUND
    assert await _handler(env).history(actor=actor, lineage_id=lineage) == before
    assert await _saved_document(env, actor, lineage) == saved_before


@pytest.mark.asyncio
async def test_stale_cursor_is_a_conflict_for_store_and_move() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    opened_cursor = imported.history_cursor
    await _store(
        env, actor, lineage, imported.document.model_copy(update={"title": "Nyare ändring"})
    )
    saved_before = await _saved_document(env, actor, lineage)

    with pytest.raises(DomainError) as store_error:
        await _undo_handler(env).handle(
            actor=actor,
            lineage_id=lineage,
            request=StoreExamWorkspaceUndoStepRequest(
                expected_cursor=opened_cursor,
                document=imported.document.model_copy(update={"title": "Gammal flik"}),
            ),
        )
    assert store_error.value.code is ErrorCode.CONFLICT

    history = await _handler(env).history(actor=actor, lineage_id=lineage)
    with pytest.raises(DomainError) as move_error:
        await _undo_handler(env).move_to_step(
            actor=actor,
            lineage_id=lineage,
            request=MoveExamWorkspaceHistoryPositionRequest(
                expected_cursor=opened_cursor, step_id=history.step_ids[0]
            ),
        )
    assert move_error.value.code is ErrorCode.CONFLICT
    assert await _saved_document(env, actor, lineage) == saved_before
    assert (
        await env.get_handler.handle(actor=actor, lineage_id=lineage)
    ).document.title == "Nyare ändring"


@pytest.mark.asyncio
async def test_the_hundred_first_step_trims_the_oldest() -> None:
    assert MAX_RETAINED_UNDO_STEPS == 100
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    for index in range(MAX_RETAINED_UNDO_STEPS + 1):
        await _store(
            env,
            actor,
            lineage,
            imported.document.model_copy(update={"title": f"Redigering {index}"}),
        )

    history = await _handler(env).history(actor=actor, lineage_id=lineage)

    assert len(history.step_ids) == MAX_RETAINED_UNDO_STEPS
    titles = [
        (
            await _handler(env).history_step(actor=actor, lineage_id=lineage, step_id=step)
        ).document.title
        for step in history.step_ids
    ]
    assert titles == [f"Redigering {index}" for index in range(1, MAX_RETAINED_UNDO_STEPS + 1)]
    assert (await _saved_document(env, actor, lineage)).title == (
        f"Redigering {MAX_RETAINED_UNDO_STEPS}"
    )
    reopened = await env.get_handler.handle(actor=actor, lineage_id=lineage)
    assert reopened.summary.version == imported.summary.version + MAX_RETAINED_UNDO_STEPS + 1


def test_the_spara_route_is_gone_and_the_position_move_route_exists() -> None:
    routes = [
        (route.path, tuple(sorted(methods)))
        for route in documents_api.router.routes
        if isinstance(route, APIRoute) and (methods := route.methods) is not None
    ]
    assert not [
        (path, methods)
        for path, methods in routes
        if path.endswith("/exam-workspace/documents/{lineage_id}") and "PUT" in methods
    ]
    assert (
        "/api/v1/apps/documents.conversion_hub/exam-workspace/documents/{lineage_id}/history/position",
        ("POST",),
    ) in routes


@pytest.mark.asyncio
async def test_one_step_store_with_one_hundred_retained_picture_steps_is_fast() -> None:
    env = _Env()
    actor = _actor()
    payload = b"picture payload kept across fifty retained steps"
    asset = NativeExamAsset(
        asset_id="asset_0123456789abcdef",
        sha256=hashlib.sha256(payload).hexdigest(),
        media_type="image/png",
        byte_length=len(payload),
    )
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    first = imported.document.items[0]
    paragraph = first.body[0]
    pictured = imported.document.model_copy(
        update={
            "assets": (asset,),
            "items": (
                first.model_copy(
                    update={
                        "body": (
                            paragraph.model_copy(
                                update={
                                    "segments": (
                                        *paragraph.segments,
                                        NativeAssetSegment(asset_id=asset.asset_id),
                                    )
                                }
                            ),
                            *first.body[1:],
                        )
                    }
                ),
                *imported.document.items[1:],
            ),
        }
    )
    await env.store.save(
        actor=actor,
        file_id=uuid4(),
        name=imported.summary.name,
        content=env.codec.build(
            content=ExamWorkspaceContainerContent(
                document=pictured.model_copy(update={"revision": 2}),
                assets_by_id={asset.asset_id: payload},
            )
        ),
        lineage_id=lineage,
        version=2,
        expected_revision=1,
        editor_step_id=lineage,
    )
    for index in range(MAX_RETAINED_UNDO_STEPS - 1):
        await _store(
            env, actor, lineage, pictured.model_copy(update={"title": f"Bildsteg {index}"})
        )

    started = time.perf_counter()
    await _store(env, actor, lineage, pictured.model_copy(update={"title": "Bildsteg hundra"}))
    elapsed = time.perf_counter() - started
    print(f"one step store with 100 retained picture steps: {elapsed:.3f} s")

    assert elapsed < 0.3, f"one step store took {elapsed:.3f} s"
