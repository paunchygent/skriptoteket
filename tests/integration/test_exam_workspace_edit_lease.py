"""Edit lease and tab guard against real PostgreSQL: one tab edits, others are refused."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.curated_apps.exam_workspace_history import (
    MoveExamWorkspaceHistoryPositionRequest,
    StoreExamWorkspaceUndoStepRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_edit_lease import (
    ExamWorkspaceEditLeaseHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_undo_steps import (
    StoreExamWorkspaceUndoStepHandler,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.exam_workspace_conversion_support import ConversionWorld, Ids
from tests.integration.exam_workspace_repair_support import editor, seed_exam
from tests.integration.infrastructure.repositories.exam_workspace_test_support import create_owner

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]


def _leases(world: ConversionWorld, clock: FixedClock) -> ExamWorkspaceEditLeaseHandler:
    return ExamWorkspaceEditLeaseHandler(
        vault_files=world.vault_files, store=world.store, clock=clock
    )


def _steps(world: ConversionWorld) -> StoreExamWorkspaceUndoStepHandler:
    return StoreExamWorkspaceUndoStepHandler(
        vault_files=world.vault_files,
        codec=world.codec,
        store=world.store,
        jobs=world.jobs,
        id_generator=Ids(),
        clock=world.clock,
    )


async def _file_bytes(world: ConversionWorld, actor: User, lineage) -> bytes:
    head = await world.vault_files.get_document_head(user_id=actor.id, document_lineage_id=lineage)
    assert head is not None
    return await world.store.load(actor=actor, vault_file=head)


async def test_claim_renew_request_and_release_roundtrip_on_real_database(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    actor = await create_owner(session_factory)
    clock = FixedClock(datetime.now(UTC))
    async with session_factory() as session:
        world = ConversionWorld(session, LocalVaultStorage(vault_root=tmp_path), clock)
        seeded = await seed_exam(world, actor)
        lineage = seeded.document_id
        leases = _leases(world, clock)
        holder, waiter = uuid4(), uuid4()

        claimed = await leases.claim(actor=actor, lineage_id=lineage, tab_id=holder)
        assert claimed.holder_tab_id == holder
        assert claimed.renewed_at == clock.now()
        stored = await world.vault_files.get_history_lease(
            user_id=actor.id, document_lineage_id=lineage
        )
        assert stored is not None and stored.holder_tab_id == holder

        await leases.request_takeover(actor=actor, lineage_id=lineage, tab_id=waiter)
        renewed = await leases.renew(actor=actor, lineage_id=lineage, tab_id=holder)
        assert renewed.takeover_requested is True
        assert renewed.takeover_requested_by == waiter

        with pytest.raises(DomainError) as error:
            await leases.claim(actor=actor, lineage_id=lineage, tab_id=waiter)
        assert error.value.code is ErrorCode.EDIT_LEASE_HELD

        await leases.release(actor=actor, lineage_id=lineage, tab_id=holder)
        taken = await leases.claim(actor=actor, lineage_id=lineage, tab_id=waiter)
        assert taken.holder_tab_id == waiter
        assert taken.takeover_requested is False


async def test_store_without_the_lease_is_refused_and_writes_nothing_on_real_database(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    actor = await create_owner(session_factory)
    clock = FixedClock(datetime.now(UTC))
    async with session_factory() as session:
        world = ConversionWorld(session, LocalVaultStorage(vault_root=tmp_path), clock)
        seeded = await seed_exam(world, actor)
        lineage = seeded.document_id
        before_bytes = await _file_bytes(world, actor, lineage)
        before = await editor(world).history(actor=actor, lineage_id=lineage)

        with pytest.raises(DomainError) as error:
            await _steps(world).handle(
                actor=actor,
                lineage_id=lineage,
                request=StoreExamWorkspaceUndoStepRequest(
                    expected_cursor=before.cursor,
                    document=seeded.model_copy(update={"title": "Tyst överskrivning"}),
                    tab_id=uuid4(),
                ),
            )
        assert error.value.code is ErrorCode.EDIT_LEASE_HELD
        assert await _file_bytes(world, actor, lineage) == before_bytes
        assert await editor(world).history(actor=actor, lineage_id=lineage) == before

        holder = uuid4()
        await _leases(world, clock).claim(actor=actor, lineage_id=lineage, tab_id=holder)
        stored = await _steps(world).handle(
            actor=actor,
            lineage_id=lineage,
            request=StoreExamWorkspaceUndoStepRequest(
                expected_cursor=before.cursor,
                document=seeded.model_copy(update={"title": "Hållarens text"}),
                tab_id=holder,
            ),
        )
        assert stored.document.title == "Hållarens text"
        assert (await editor(world).history(actor=actor, lineage_id=lineage)) != before


async def test_position_move_without_the_lease_is_refused_on_real_database(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    actor = await create_owner(session_factory)
    clock = FixedClock(datetime.now(UTC))
    async with session_factory() as session:
        world = ConversionWorld(session, LocalVaultStorage(vault_root=tmp_path), clock)
        seeded = await seed_exam(world, actor)
        lineage = seeded.document_id
        holder = uuid4()
        await _leases(world, clock).claim(actor=actor, lineage_id=lineage, tab_id=holder)
        stored = await _steps(world).handle(
            actor=actor,
            lineage_id=lineage,
            request=StoreExamWorkspaceUndoStepRequest(
                expected_cursor=(
                    await editor(world).history(actor=actor, lineage_id=lineage)
                ).cursor,
                document=seeded.model_copy(update={"title": "Hållarens text"}),
                tab_id=holder,
            ),
        )
        before_bytes = await _file_bytes(world, actor, lineage)

        with pytest.raises(DomainError) as error:
            await _steps(world).move_to_step(
                actor=actor,
                lineage_id=lineage,
                request=MoveExamWorkspaceHistoryPositionRequest(
                    expected_cursor=stored.history.cursor,
                    step_id=stored.history.step_ids[0],
                    tab_id=uuid4(),
                ),
            )
        assert error.value.code is ErrorCode.EDIT_LEASE_HELD
        assert await _file_bytes(world, actor, lineage) == before_bytes
