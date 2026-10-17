"""Payload exclusion cannot consume a second application-pool connection."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.exam_workspace_conversion_support import ConversionWorld
from tests.integration.exam_workspace_repair_support import seed_exam
from tests.integration.infrastructure.repositories.exam_workspace_test_support import create_owner

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]


async def test_payload_guard_completes_with_one_slot_pool_and_an_existing_transaction(
    migrated_db: str, tmp_path: Path
) -> None:
    engine = create_async_engine(migrated_db, pool_size=1, max_overflow=0, pool_timeout=0.2)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        actor = await create_owner(factory)
        async with factory() as session:
            # Auth or application reads can already own the only pool connection.
            assert await session.scalar(text("SELECT 1")) == 1
            assert session.in_transaction()
            world = ConversionWorld(
                session, LocalVaultStorage(vault_root=tmp_path), FixedClock(datetime.now(UTC))
            )
            async with asyncio.timeout(5):
                document = await seed_exam(world, actor)
                reopened = await world.opened(actor, document.document_id)
            assert reopened.document == document
    finally:
        await engine.dispose()
