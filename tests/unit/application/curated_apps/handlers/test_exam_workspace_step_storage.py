"""Per-step undo storage: one row per step, pictures once per exam."""

import hashlib
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.exam_workspace_history import (
    MAX_RETAINED_UNDO_STEPS,
    MoveExamWorkspaceHistoryPositionRequest,
    StoreExamWorkspaceUndoStepRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_undo_steps import (
    StoreExamWorkspaceUndoStepHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import ExamWorkspaceContainerContent
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import NativeAssetSegment
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
)
from skriptoteket.domain.identity.models import User
from tests.unit.application.curated_apps.handlers.test_conversion_hub_jobs import (
    SequenceIdGenerator,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _actor,
    _Env,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_history_contract import (
    _handler,
    _undo_handler,
)

_FIXTURE = Path("tests/fixtures/exam_conversion/native_workspace_grammatik.json")

_WRITE_CALLS = frozenset(
    {
        "insert_history_step",
        "delete_history_steps",
        "upsert_history_head",
        "delete_orphan_history_assets",
    }
)


def _asset(payload: bytes) -> NativeExamAsset:
    return NativeExamAsset(
        asset_id=f"asset_{hashlib.sha256(payload).hexdigest()[:16]}",
        sha256=hashlib.sha256(payload).hexdigest(),
        media_type="image/png",
        byte_length=len(payload),
    )


def _pictured(document: NativeExamDocument, asset: NativeExamAsset) -> NativeExamDocument:
    first = document.items[0]
    paragraph = first.body[0]
    return document.model_copy(
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
                *document.items[1:],
            ),
        }
    )


async def _seed_pictured(
    env: _Env, actor: User
) -> tuple[UUID, NativeExamDocument, NativeExamAsset, bytes]:
    """Seed an exam whose baseline and file hold one picture, like a picture import."""
    payload = b"picture kept across a picture change"
    asset = _asset(payload)
    plain = NativeExamDocument.model_validate_json(_FIXTURE.read_bytes())
    lineage = uuid4()
    baseline = _pictured(plain, asset).model_copy(update={"document_id": lineage})
    await env.store.save(
        actor=actor,
        file_id=uuid4(),
        name="bild.provdokument.zip",
        content=env.codec.build(
            content=ExamWorkspaceContainerContent(
                document=baseline, assets_by_id={asset.asset_id: payload}
            )
        ),
        lineage_id=lineage,
        version=1,
    )
    return lineage, plain.model_copy(update={"document_id": lineage}), asset, payload


async def _store(env: _Env, actor: User, lineage: UUID, document: NativeExamDocument) -> UUID:
    cursor = (await _handler(env).history(actor=actor, lineage_id=lineage)).cursor
    response = await _undo_handler(env).handle(
        actor=actor,
        lineage_id=lineage,
        request=StoreExamWorkspaceUndoStepRequest(expected_cursor=cursor, document=document),
    )
    return response.history.position_step_id


async def _write_file(
    env: _Env, actor: User, lineage: UUID, document: NativeExamDocument, payload: bytes
) -> None:
    """Deliver a pictured file revision the way conversion delivery does: file, not step."""
    asset = document.assets[0]
    head = env.vault_files.files[
        next(
            file.id
            for file in env.vault_files.files.values()
            if file.document_lineage_id == lineage and file.export_format is None
        )
    ]
    version = (head.document_version or 1) + 1
    await env.store.save(
        actor=actor,
        file_id=uuid4(),
        name=head.name,
        content=env.codec.build(
            content=ExamWorkspaceContainerContent(
                document=document.model_copy(update={"revision": version}),
                assets_by_id={asset.asset_id: payload},
            )
        ),
        lineage_id=lineage,
        version=version,
        expected_revision=head.document_version,
        preserve_editor_position=True,
    )


def _step_rows(env: _Env, actor: User, lineage: UUID) -> dict[UUID, object]:
    return {
        step_id: record
        for (user_id, row_lineage, step_id), record in env.vault_files.history_steps.items()
        if user_id == actor.id and row_lineage == lineage
    }


def _write_calls(env: _Env) -> list[str]:
    return [name for name, _ in env.vault_files.calls if name in _WRITE_CALLS]


@pytest.mark.asyncio
async def test_one_autosave_writes_one_step_row_and_leaves_other_step_rows_alone() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    for title in ("Ett", "Två", "Tre"):
        await _store(env, actor, lineage, imported.document.model_copy(update={"title": title}))
    before = _step_rows(env, actor, lineage)
    env.vault_files.calls.clear()

    await _store(env, actor, lineage, imported.document.model_copy(update={"title": "Fyra"}))

    after = _step_rows(env, actor, lineage)
    assert len(after) == len(before) + 1
    assert set(after) - set(before) != set()
    for step_id, record in before.items():
        assert after[step_id] == record
    assert _write_calls(env).count("insert_history_step") == 1
    assert "delete_history_steps" not in _write_calls(env)


@pytest.mark.asyncio
async def test_hundred_and_first_store_drops_the_oldest_step_row() -> None:
    assert MAX_RETAINED_UNDO_STEPS == 100
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    first = await _store(
        env, actor, lineage, imported.document.model_copy(update={"title": "Noll"})
    )
    for index in range(1, MAX_RETAINED_UNDO_STEPS + 1):
        await _store(
            env,
            actor,
            lineage,
            imported.document.model_copy(update={"title": f"Redigering {index}"}),
        )

    rows = _step_rows(env, actor, lineage)
    assert len(rows) == MAX_RETAINED_UNDO_STEPS + 1
    assert first not in rows
    history = await _handler(env).history(actor=actor, lineage_id=lineage)
    assert len(history.step_ids) == MAX_RETAINED_UNDO_STEPS
    assert first not in history.step_ids


@pytest.mark.asyncio
async def test_position_move_updates_only_the_history_row() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    first = await _store(env, actor, lineage, imported.document.model_copy(update={"title": "Ett"}))
    await _store(env, actor, lineage, imported.document.model_copy(update={"title": "Två"}))
    before = _step_rows(env, actor, lineage)
    env.vault_files.calls.clear()

    cursor = (await _handler(env).history(actor=actor, lineage_id=lineage)).cursor
    await _undo_handler(env).move_to_step(
        actor=actor,
        lineage_id=lineage,
        request=MoveExamWorkspaceHistoryPositionRequest(expected_cursor=cursor, step_id=first),
    )

    assert _step_rows(env, actor, lineage) == before
    assert _write_calls(env) == ["upsert_history_head"]


@pytest.mark.asyncio
async def test_undo_across_a_picture_change_keeps_the_picture() -> None:
    env = _Env()
    actor = _actor()
    lineage, plain, asset, payload = await _seed_pictured(env, actor)
    await _store(env, actor, lineage, plain.model_copy(update={"title": "Utan bild"}))

    restored = await _handler(env).history_step(actor=actor, lineage_id=lineage, step_id=lineage)

    assert restored.document.assets == (asset,)
    served = await StoreExamWorkspaceUndoStepHandler(
        vault_files=env.vault_files,
        codec=env.codec,
        store=env.store,
        id_generator=SequenceIdGenerator([uuid4()]),
        jobs=env.enrichment_jobs,
    ).move_to_step(
        actor=actor,
        lineage_id=lineage,
        request=MoveExamWorkspaceHistoryPositionRequest(
            expected_cursor=(await _handler(env).history(actor=actor, lineage_id=lineage)).cursor,
            step_id=lineage,
        ),
    )
    assert served.document.assets == (asset,)
    reopened = await env.get_handler.handle(actor=actor, lineage_id=lineage)
    assert reopened.document.assets == (asset,)
    assert env.vault_files.history_assets[(actor.id, lineage, asset.asset_id)] == payload


@pytest.mark.asyncio
async def test_trim_deletes_the_picture_no_step_or_file_uses() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    payload = b"picture dropped after trimming"
    asset = _asset(payload)
    await _write_file(env, actor, lineage, _pictured(imported.document, asset), payload)
    await _store(env, actor, lineage, _pictured(imported.document, asset))
    for index in range(MAX_RETAINED_UNDO_STEPS):
        await _store(
            env,
            actor,
            lineage,
            imported.document.model_copy(update={"title": f"Utan bild {index}"}),
        )

    assert (actor.id, lineage, asset.asset_id) not in env.vault_files.history_assets


@pytest.mark.asyncio
async def test_trim_keeps_the_picture_the_baseline_still_uses() -> None:
    env = _Env()
    actor = _actor()
    lineage, plain, asset, payload = await _seed_pictured(env, actor)
    for index in range(MAX_RETAINED_UNDO_STEPS + 1):
        await _store(env, actor, lineage, plain.model_copy(update={"title": f"Utan bild {index}"}))

    assert env.vault_files.history_assets[(actor.id, lineage, asset.asset_id)] == payload
    kept = await _handler(env).history_step(actor=actor, lineage_id=lineage, step_id=lineage)
    assert kept.document.assets == (asset,)


@pytest.mark.asyncio
async def test_rewrite_keeps_the_picture_only_the_file_uses() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    payload = b"picture only the saved file still names"
    asset = _asset(payload)
    await _write_file(env, actor, lineage, _pictured(imported.document, asset), payload)
    await _store(env, actor, lineage, _pictured(imported.document, asset))
    state = await env.store.get_history(actor=actor, lineage_id=lineage)
    # Every pictured step is trimmed, but the saved file still names the picture.
    trimmed = state.model_copy(update={"steps": (), "current_step_id": state.baseline.step_id})

    await env.store.put_history(actor=actor, lineage_id=lineage, history=trimmed)

    assert env.vault_files.history_assets[(actor.id, lineage, asset.asset_id)] == payload


@pytest.mark.asyncio
async def test_reopen_without_a_history_row_recreates_the_baseline_from_the_file() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    await _store(env, actor, lineage, imported.document.model_copy(update={"title": "Borta"}))
    env.vault_files.history_heads.pop((actor.id, lineage))
    env.vault_files.history_steps = {
        key: record
        for key, record in env.vault_files.history_steps.items()
        if key[:2] != (actor.id, lineage)
    }
    env.vault_files.history_assets = {
        key: payload
        for key, payload in env.vault_files.history_assets.items()
        if key[:2] != (actor.id, lineage)
    }

    reopened = await env.get_handler.handle(actor=actor, lineage_id=lineage)
    history = await _handler(env).history(actor=actor, lineage_id=lineage)

    assert reopened.document.title == "Borta"
    assert history.step_ids == ()
    assert history.baseline_step_id == lineage
    assert history.position_step_id == lineage
