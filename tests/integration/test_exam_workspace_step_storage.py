"""Per-step undo storage against real PostgreSQL: one row per step, pictures once."""

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.curated_apps.exam_workspace_history import (
    MAX_RETAINED_UNDO_STEPS,
    MoveExamWorkspaceHistoryPositionRequest,
    StoreExamWorkspaceUndoStepRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_assets import (
    GetExamWorkspaceAssetHandler,
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
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.exam_workspace_conversion_support import (
    ConversionWorld,
    Ids,
    lease_tab,
)
from tests.integration.exam_workspace_repair_support import editor, seed_exam
from tests.integration.infrastructure.repositories.exam_workspace_test_support import create_owner

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]

_FIXTURE = Path("tests/fixtures/exam_conversion/native_workspace_grammatik.json")


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


def _steps(world: ConversionWorld) -> StoreExamWorkspaceUndoStepHandler:
    return StoreExamWorkspaceUndoStepHandler(
        clock=world.clock,
        vault_files=world.vault_files,
        codec=world.codec,
        store=world.store,
        id_generator=Ids(),
        jobs=world.jobs,
    )


async def _store(world: ConversionWorld, actor: User, lineage: UUID, document: NativeExamDocument):
    cursor = (await world.store.get_history(actor=actor, lineage_id=lineage)).cursor
    return await _steps(world).handle(
        actor=actor,
        lineage_id=lineage,
        request=StoreExamWorkspaceUndoStepRequest(
            expected_cursor=cursor,
            document=document,
            tab_id=await lease_tab(world, actor, lineage),
        ),
    )


async def _seed_pictured(
    world: ConversionWorld, actor: User
) -> tuple[UUID, NativeExamDocument, NativeExamAsset, bytes]:
    payload = b"integration picture stored once per exam"
    asset = _asset(payload)
    plain = NativeExamDocument.model_validate_json(_FIXTURE.read_bytes())
    lineage = uuid4()
    baseline = _pictured(plain, asset).model_copy(update={"document_id": lineage, "revision": 1})
    await world.store.save(
        actor=actor,
        file_id=uuid4(),
        name="bild.provdokument.zip",
        content=world.codec.build(
            content=ExamWorkspaceContainerContent(
                document=baseline, assets_by_id={asset.asset_id: payload}
            )
        ),
        lineage_id=lineage,
        version=1,
    )
    return lineage, plain.model_copy(update={"document_id": lineage}), asset, payload


async def test_step_storage_keeps_100_steps_and_drops_oldest_on_real_database(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    assert MAX_RETAINED_UNDO_STEPS == 100
    actor = await create_owner(session_factory)
    async with session_factory() as session:
        world = ConversionWorld(
            session, LocalVaultStorage(vault_root=tmp_path), FixedClock(datetime.now(UTC))
        )
        seeded = await seed_exam(world, actor)
        lineage = seeded.document_id
        first_response = await _store(
            world, actor, lineage, seeded.model_copy(update={"title": "Noll"})
        )
        first = first_response.history.position_step_id
        cursor = first_response.history.cursor
        for index in range(1, MAX_RETAINED_UNDO_STEPS + 1):
            response = await _steps(world).handle(
                actor=actor,
                lineage_id=lineage,
                request=StoreExamWorkspaceUndoStepRequest(
                    tab_id=await lease_tab(world, actor, lineage),
                    expected_cursor=cursor,
                    document=seeded.model_copy(update={"title": f"Redigering {index}"}),
                ),
            )
            cursor = response.history.cursor
        refs = await world.vault_files.list_history_step_refs(
            user_id=actor.id, document_lineage_id=lineage
        )
        step_ids = [ref.step_id for ref in refs]
        assert len(refs) == MAX_RETAINED_UNDO_STEPS + 1
        assert first not in step_ids
        history = await editor(world).history(actor=actor, lineage_id=lineage)
        assert len(history.step_ids) == MAX_RETAINED_UNDO_STEPS
        assert first not in history.step_ids
        reopened = await world.opened(actor, lineage)
        assert reopened.document.title == f"Redigering {MAX_RETAINED_UNDO_STEPS}"


async def test_autosave_writes_single_step_row_on_real_database(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    actor = await create_owner(session_factory)
    async with session_factory() as session:
        world = ConversionWorld(
            session, LocalVaultStorage(vault_root=tmp_path), FixedClock(datetime.now(UTC))
        )
        seeded = await seed_exam(world, actor)
        lineage = seeded.document_id
        for title in ("Ett", "Två", "Tre"):
            await _store(world, actor, lineage, seeded.model_copy(update={"title": title}))
        before = {
            record.step_id: record
            for record in await world.vault_files.list_history_steps(
                user_id=actor.id, document_lineage_id=lineage
            )
        }

        await _store(world, actor, lineage, seeded.model_copy(update={"title": "Fyra"}))

        after = {
            record.step_id: record
            for record in await world.vault_files.list_history_steps(
                user_id=actor.id, document_lineage_id=lineage
            )
        }
        assert len(after) == len(before) + 1
        assert set(after) - set(before) != set()
        for step_id, record in before.items():
            assert after[step_id] == record


async def test_undo_across_picture_change_keeps_picture_on_real_database(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    actor = await create_owner(session_factory)
    async with session_factory() as session:
        world = ConversionWorld(
            session, LocalVaultStorage(vault_root=tmp_path), FixedClock(datetime.now(UTC))
        )
        lineage, plain, asset, payload = await _seed_pictured(world, actor)
        await _store(world, actor, lineage, plain.model_copy(update={"title": "Utan bild"}))

        restored = await editor(world).history_step(
            actor=actor, lineage_id=lineage, step_id=lineage
        )
        assert restored.document.assets == (asset,)
        served = await GetExamWorkspaceAssetHandler(
            vault_files=world.vault_files, codec=world.codec, store=world.store
        ).handle(actor=actor, lineage_id=lineage, asset_id=asset.asset_id)
        assert served.content == payload

        history = await editor(world).history(actor=actor, lineage_id=lineage)
        await _steps(world).move_to_step(
            actor=actor,
            lineage_id=lineage,
            request=MoveExamWorkspaceHistoryPositionRequest(
                tab_id=await lease_tab(world, actor, lineage),
                expected_cursor=history.cursor,
                step_id=lineage,
            ),
        )
        reopened = await world.opened(actor, lineage)
        assert reopened.document.assets == (asset,)
        head = await world.vault_files.get_document_head(
            user_id=actor.id, document_lineage_id=lineage
        )
        assert head is not None
        assert world.codec.parse(
            content=await world.store.load(actor=actor, vault_file=head)
        ).assets_by_id == {asset.asset_id: payload}


async def test_trim_removes_orphan_picture_but_keeps_baseline_picture_on_real_database(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    actor = await create_owner(session_factory)
    async with session_factory() as session:
        world = ConversionWorld(
            session, LocalVaultStorage(vault_root=tmp_path), FixedClock(datetime.now(UTC))
        )
        lineage, plain, asset, payload = await _seed_pictured(world, actor)
        other_payload = b"integration picture trimmed away with its last step"
        other = _asset(other_payload)
        other_id = other.asset_id
        pictured = _pictured(plain, other)
        await world.store.save(
            actor=actor,
            file_id=uuid4(),
            name="bild.provdokument.zip",
            content=world.codec.build(
                content=ExamWorkspaceContainerContent(
                    document=pictured.model_copy(update={"revision": 2}),
                    assets_by_id={other_id: other_payload},
                )
            ),
            lineage_id=lineage,
            version=2,
            expected_revision=1,
            preserve_editor_position=True,
        )
        await _store(world, actor, lineage, pictured)
        cursor = (await editor(world).history(actor=actor, lineage_id=lineage)).cursor
        for index in range(MAX_RETAINED_UNDO_STEPS):
            response = await _steps(world).handle(
                actor=actor,
                lineage_id=lineage,
                request=StoreExamWorkspaceUndoStepRequest(
                    tab_id=await lease_tab(world, actor, lineage),
                    expected_cursor=cursor,
                    document=plain.model_copy(update={"title": f"Utan bild {index}"}),
                ),
            )
            cursor = response.history.cursor

        assert (
            await world.vault_files.get_history_assets(
                user_id=actor.id, document_lineage_id=lineage, asset_ids=(other_id,)
            )
            == {}
        )
        assert (
            await world.vault_files.get_history_assets(
                user_id=actor.id, document_lineage_id=lineage, asset_ids=(asset.asset_id,)
            )
        ) == {asset.asset_id: payload}
