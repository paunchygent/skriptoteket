"""Persistent undo and copy behavior exercised through application handlers."""

import hashlib
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.exam_workspace import SaveExamWorkspaceDocumentRequest
from skriptoteket.application.curated_apps.exam_workspace_history import (
    SaveAsExamWorkspaceDocumentRequest,
    StoreExamWorkspaceUndoStepRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_assets import (
    GetExamWorkspaceAssetHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    SaveExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_undo_steps import (
    StoreExamWorkspaceUndoStepHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import ExamWorkspaceContainerContent
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import NativeAssetSegment
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    ExamCourseChoice,
    NativeExamAsset,
    NativeExamHeader,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    NativeExportBlocker,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from tests.unit.application.curated_apps.handlers.test_conversion_hub_jobs import (
    SequenceIdGenerator,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _actor,
    _Env,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_document_test_support import (
    with_next_revision,
)


def _handler(env: _Env) -> SaveExamWorkspaceDocumentHandler:
    """Create a fresh request handler over the same persistence ports."""
    return SaveExamWorkspaceDocumentHandler(
        vault_files=env.vault_files,
        codec=env.codec,
        store=env.store,
        id_generator=SequenceIdGenerator([uuid4() for _ in range(100)]),
        jobs=env.enrichment_jobs,
    )


def _undo_handler(env: _Env) -> StoreExamWorkspaceUndoStepHandler:
    return StoreExamWorkspaceUndoStepHandler(
        vault_files=env.vault_files,
        codec=env.codec,
        store=env.store,
        id_generator=SequenceIdGenerator([uuid4() for _ in range(100)]),
        jobs=env.enrichment_jobs,
    )


@pytest.mark.asyncio
async def test_twelve_autosaves_keep_ten_steps_across_save_and_fresh_requests() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    handler = _handler(env)
    initial = await handler.history(actor=actor, lineage_id=lineage)
    assert initial.step_ids == ()  # Import is the baseline, never a counted undo step.
    for index in range(12):
        await _undo_handler(env).handle(
            actor=actor,
            lineage_id=lineage,
            request=StoreExamWorkspaceUndoStepRequest(
                expected_cursor=(await handler.history(actor=actor, lineage_id=lineage)).cursor,
                document=imported.document.model_copy(
                    update={"revision": 2, "title": f"Lärarens redigering {index}"}
                ),
            ),
        )
    history = await _handler(env).history(actor=actor, lineage_id=lineage)
    assert len(history.step_ids) == 10
    titles = [
        (
            await _handler(env).history_step(actor=actor, lineage_id=lineage, step_id=step)
        ).document.title
        for step in history.step_ids
    ]
    assert titles == [f"Lärarens redigering {index}" for index in range(2, 12)]
    reopened = await env.get_handler.handle(actor=actor, lineage_id=lineage)
    assert reopened.document.title == "Lärarens redigering 11"
    assert reopened.history_cursor == history.cursor
    # Autosave must not overwrite the durable exam file or create vault rows.
    saved_file = env.vault_files.files[imported.summary.vault_file_id]
    saved_container = env.codec.parse(
        content=await env.store.load(actor=actor, vault_file=saved_file)
    )
    assert saved_container.document.title == imported.document.title
    assert len(await env.vault_files.list_active_for_user(user_id=actor.id)) == 1
    await handler.handle(
        actor=actor,
        lineage_id=lineage,
        request=SaveExamWorkspaceDocumentRequest(
            expected_revision=1,
            document=reopened.document.model_copy(update={"revision": 2}),
            position_step_id=history.position_step_id,
        ),
    )
    after_save = await _handler(env).history(actor=actor, lineage_id=lineage)
    assert after_save.step_ids == history.step_ids
    assert after_save.baseline_step_id == history.baseline_step_id
    assert after_save.cursor != history.cursor
    reopened_after_save = await env.get_handler.handle(actor=actor, lineage_id=lineage)
    assert reopened_after_save.history_cursor == after_save.cursor
    previous = await _handler(env).history_step(
        actor=actor, lineage_id=lineage, step_id=history.step_ids[-2]
    )
    assert previous.document.title == "Lärarens redigering 10"


@pytest.mark.asyncio
async def test_edit_after_undo_discards_redo_without_damaging_other_exam_history() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    other = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    handler = _handler(env)
    for title in ("Första", "Andra", "Tredje"):
        await _undo_handler(env).handle(
            actor=actor,
            lineage_id=lineage,
            request=StoreExamWorkspaceUndoStepRequest(
                expected_cursor=(await handler.history(actor=actor, lineage_id=lineage)).cursor,
                document=imported.document.model_copy(update={"revision": 2, "title": title}),
            ),
        )
    before = await handler.history(actor=actor, lineage_id=lineage)
    undone = await handler.history_step(actor=actor, lineage_id=lineage, step_id=before.step_ids[0])
    await _undo_handler(env).handle(
        actor=actor,
        lineage_id=lineage,
        request=StoreExamWorkspaceUndoStepRequest(
            expected_cursor=before.cursor,
            document=undone.document.model_copy(update={"title": "Ny gren"}),
            after_step_id=before.step_ids[0],
        ),
    )
    after = await _handler(env).history(actor=actor, lineage_id=lineage)
    assert len(after.step_ids) == 2
    assert after.step_ids[0] == before.step_ids[0]
    assert not set(before.step_ids[1:]) & set(after.step_ids)
    for removed_step in before.step_ids[1:]:
        with pytest.raises(DomainError) as error:
            await handler.history_step(actor=actor, lineage_id=lineage, step_id=removed_step)
        assert error.value.code is ErrorCode.NOT_FOUND
    other_history = await handler.history(actor=actor, lineage_id=other.summary.lineage_id)
    assert other_history.step_ids == ()
    assert (
        await env.get_handler.handle(actor=actor, lineage_id=lineage)
    ).document.title == "Ny gren"


@pytest.mark.asyncio
async def test_undo_response_roundtrips_through_existing_save_revision_contract() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    edited = await _undo_handler(env).handle(
        actor=actor,
        lineage_id=lineage,
        request=StoreExamWorkspaceUndoStepRequest(
            expected_cursor=imported.history_cursor,
            document=imported.document.model_copy(update={"title": "Aktuell redigering"}),
        ),
    )
    saved = await _handler(env).handle(
        actor=actor,
        lineage_id=lineage,
        request=SaveExamWorkspaceDocumentRequest(
            expected_revision=edited.document.revision,
            document=with_next_revision(edited.document),
            position_step_id=edited.history.position_step_id,
        ),
    )
    assert edited.document.revision == imported.document.revision
    assert saved.summary.vault_file_id == imported.summary.vault_file_id
    assert saved.document.revision == imported.document.revision + 1
    head = env.vault_files.files[imported.summary.vault_file_id]
    durable = env.codec.parse(content=await env.store.load(actor=actor, vault_file=head))
    assert durable.document.title == "Aktuell redigering"
    assert durable.document.revision == saved.document.revision


@pytest.mark.asyncio
async def test_undo_response_carries_the_gates_title_verdict_for_the_stored_step() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    blank = await _undo_handler(env).handle(
        actor=actor,
        lineage_id=imported.summary.lineage_id,
        request=StoreExamWorkspaceUndoStepRequest(
            expected_cursor=imported.history_cursor,
            document=imported.document.model_copy(update={"title": "?!..."}),
        ),
    )
    titled = await _undo_handler(env).handle(
        actor=actor,
        lineage_id=imported.summary.lineage_id,
        request=StoreExamWorkspaceUndoStepRequest(
            expected_cursor=blank.history.cursor,
            document=blank.document.model_copy(update={"title": "Prov 1"}),
        ),
    )

    assert NativeExportBlocker(item_id=None, reason="title_without_text") in blank.export_blockers
    assert all(blocker.item_id is not None for blocker in titled.export_blockers)


@pytest.mark.asyncio
@pytest.mark.parametrize("intervening_write", ["autosave", "save"])
async def test_stale_cursor_cannot_overwrite_an_intervening_editor_write(
    intervening_write: str,
) -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    handler = _handler(env)
    opened_history = await handler.history(actor=actor, lineage_id=lineage)
    winning_document = imported.document.model_copy(
        update={"revision": 2, "title": "Nyare ändring"}
    )
    if intervening_write == "autosave":
        accepted = await _undo_handler(env).handle(
            actor=actor,
            lineage_id=lineage,
            request=StoreExamWorkspaceUndoStepRequest(
                expected_cursor=opened_history.cursor, document=winning_document
            ),
        )
        assert accepted.history.cursor != opened_history.cursor
    else:
        await handler.handle(
            actor=actor,
            lineage_id=lineage,
            request=SaveExamWorkspaceDocumentRequest(
                expected_revision=1,
                document=winning_document,
                position_step_id=opened_history.position_step_id,
            ),
        )
    before_stale_attempt = await handler.history(actor=actor, lineage_id=lineage)
    with pytest.raises(DomainError) as error:
        await _undo_handler(env).handle(
            actor=actor,
            lineage_id=lineage,
            request=StoreExamWorkspaceUndoStepRequest(
                expected_cursor=opened_history.cursor,
                document=imported.document.model_copy(
                    update={"revision": 2, "title": "Gammal flik"}
                ),
            ),
        )
    assert error.value.code is ErrorCode.CONFLICT
    assert await handler.history(actor=actor, lineage_id=lineage) == before_stale_attempt
    assert (
        await env.get_handler.handle(actor=actor, lineage_id=lineage)
    ).document.title == "Nyare ändring"


@pytest.mark.asyncio
async def test_history_picture_can_be_restored_after_save_removes_it() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    payload = b"picture payload preserved by the undo container"
    asset = NativeExamAsset(
        asset_id="asset_0123456789abcdef",
        sha256=hashlib.sha256(payload).hexdigest(),
        media_type="image/png",
        byte_length=len(payload),
    )
    first = imported.document.items[0]
    paragraph = first.body[0]
    pictured = imported.document.model_copy(
        update={
            "revision": 2,
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
                document=pictured, assets_by_id={asset.asset_id: payload}
            )
        ),
        lineage_id=lineage,
        version=2,
        expected_revision=1,
        editor_step_id=lineage,
    )
    handler = _handler(env)
    await _undo_handler(env).handle(
        actor=actor,
        lineage_id=lineage,
        request=StoreExamWorkspaceUndoStepRequest(
            expected_cursor=(await handler.history(actor=actor, lineage_id=lineage)).cursor,
            document=pictured.model_copy(update={"revision": 3}),
        ),
    )
    history = await handler.history(actor=actor, lineage_id=lineage)
    await handler.handle(
        actor=actor,
        lineage_id=lineage,
        request=SaveExamWorkspaceDocumentRequest(
            expected_revision=2,
            document=imported.document.model_copy(update={"revision": 3}),
            position_step_id=history.position_step_id,
        ),
    )
    restored = await _handler(env).history_step(
        actor=actor, lineage_id=lineage, step_id=history.step_ids[-1]
    )
    assert restored.document.assets == (asset,)
    served = await GetExamWorkspaceAssetHandler(
        vault_files=env.vault_files, codec=env.codec, store=env.store
    ).handle(actor=actor, lineage_id=lineage, asset_id=asset.asset_id)
    assert served.content == payload
    assert served.media_type == "image/png"
    await _handler(env).handle(
        actor=actor,
        lineage_id=lineage,
        request=SaveExamWorkspaceDocumentRequest(
            expected_revision=3,
            document=restored.document.model_copy(update={"revision": 4}),
            position_step_id=(
                await handler.history(actor=actor, lineage_id=lineage)
            ).position_step_id,
        ),
    )
    saved_file = env.vault_files.files[imported.summary.vault_file_id]
    restored_container = env.codec.parse(
        content=await env.store.load(actor=actor, vault_file=saved_file)
    )
    assert restored_container.assets_by_id == {asset.asset_id: payload}


@pytest.mark.asyncio
async def test_save_as_copies_editor_content_and_course_without_original_history() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    handler = _handler(env)
    editor = imported.document.model_copy(
        update={
            "revision": 2,
            "title": "Osparade ändringar",
            "header": NativeExamHeader(course=ExamCourseChoice(key="ENGENG06", name="Engelska 6")),
        }
    )
    await _undo_handler(env).handle(
        actor=actor,
        lineage_id=imported.summary.lineage_id,
        request=StoreExamWorkspaceUndoStepRequest(
            expected_cursor=(
                await handler.history(actor=actor, lineage_id=imported.summary.lineage_id)
            ).cursor,
            document=editor,
        ),
    )
    original_history = await handler.history(actor=actor, lineage_id=imported.summary.lineage_id)
    copied = await handler.save_as(
        actor=actor,
        lineage_id=imported.summary.lineage_id,
        request=SaveAsExamWorkspaceDocumentRequest(name="Prov v.42 (kopia)", document=editor),
    )
    assert copied.document.document_id != imported.document.document_id
    assert copied.summary.vault_file_id != imported.summary.vault_file_id
    assert copied.document.revision == 1
    assert copied.document.title == editor.title
    assert copied.document.items == editor.items
    assert copied.document.header == editor.header
    assert copied.summary.name == "Prov v.42 (kopia).provdokument.zip"
    assert (await handler.history(actor=actor, lineage_id=copied.summary.lineage_id)).step_ids == ()
    assert (
        await handler.history(actor=actor, lineage_id=imported.summary.lineage_id)
        == original_history
    )
    assert len(await env.vault_files.list_active_for_user(user_id=actor.id)) == 2
    with pytest.raises(DomainError) as error:
        await handler.save_as(
            actor=actor,
            lineage_id=imported.summary.lineage_id,
            request=SaveAsExamWorkspaceDocumentRequest(name="Prov v.42 (kopia)", document=editor),
        )
    assert (error.value.details or {}).get("code") == "vault_name_in_use"
    assert len(await env.vault_files.list_active_for_user(user_id=actor.id)) == 2
