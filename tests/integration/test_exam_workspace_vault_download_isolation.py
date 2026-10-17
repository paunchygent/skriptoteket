"""Mina filer downloads cannot expose an exam/export's uncommitted payload."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceExportTarget
from skriptoteket.application.scripting.handlers.download_vault_file import DownloadVaultFileHandler
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.exam_workspace_conversion_support import ConversionWorld
from tests.integration.exam_workspace_repair_support import seed_exam
from tests.integration.infrastructure.repositories.exam_workspace_test_support import create_owner
from tests.integration.test_exam_workspace_payload_compensation import exporter

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]


@pytest.mark.parametrize("kind", ["exam", "export"])
async def test_vault_download_waits_for_pending_payload_write_then_returns_committed_bytes(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path, kind: str
) -> None:
    actor = await create_owner(session_factory)
    clock = FixedClock(datetime.now(UTC))
    storage = LocalVaultStorage(vault_root=tmp_path)
    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        document = await seed_exam(world, actor)
        lineage = document.document_id
        if kind == "export":
            row = await exporter(world).save(
                actor=actor,
                lineage_id=lineage,
                target=ExamWorkspaceExportTarget.QTI,
                expected_revision=1,
            )
        else:
            head = await world.vault_files.get_document_head(
                user_id=actor.id, document_lineage_id=lineage
            )
            assert head is not None
            row = head
        file_id = row.id
        original = await storage.read_file(user_id=actor.id, file_id=file_id)
    written = asyncio.Event()
    rollback = asyncio.Event()

    async def pending_writer() -> None:
        async with session_factory() as session:
            world = ConversionWorld(session, storage, clock)
            with pytest.raises(RuntimeError, match="injected rollback"):
                async with world.store.transaction(user_id=actor.id, lineage_id=lineage):
                    await world.teacher_save(
                        actor, document.model_copy(update={"title": "Never committed"})
                    )
                    if kind == "export":
                        await exporter(world).save(
                            actor=actor,
                            lineage_id=lineage,
                            target=ExamWorkspaceExportTarget.QTI,
                            expected_revision=2,
                        )
                    assert await storage.read_file(user_id=actor.id, file_id=file_id) != original
                    written.set()
                    await rollback.wait()
                    raise RuntimeError("injected rollback")

    async def download() -> bytes:
        async with session_factory() as session:
            world = ConversionWorld(session, storage, clock)
            name, content = await DownloadVaultFileHandler(
                uow=world.uow, vault_files=world.vault_files, vault_storage=storage
            ).handle(actor=actor, file_id=file_id)
            assert name == row.name
            return content

    writer = asyncio.create_task(pending_writer())
    reader: asyncio.Task[bytes] | None = None
    try:
        await asyncio.wait_for(written.wait(), timeout=10)
        reader = asyncio.create_task(download())
        async with asyncio.timeout(10), session_factory() as observer:
            while not reader.done():
                waiting = await observer.scalar(
                    text(
                        "SELECT EXISTS (SELECT 1 FROM pg_locks "
                        "WHERE locktype = 'advisory' AND NOT granted)"
                    )
                )
                if waiting:
                    break
                await asyncio.sleep(0.01)
    finally:
        rollback.set()
        await asyncio.wait_for(writer, timeout=10)
    assert reader is not None
    downloaded = await asyncio.wait_for(reader, timeout=10)
    assert downloaded == original
    assert await storage.read_file(user_id=actor.id, file_id=file_id) == original
