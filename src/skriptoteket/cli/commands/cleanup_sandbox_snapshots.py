from __future__ import annotations

import asyncio

import typer

from skriptoteket.cli._db import open_session
from skriptoteket.config import Settings
from skriptoteket.infrastructure.clock import UTCClock
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.repositories.sandbox_snapshot_repository import (
    PostgreSQLSandboxSnapshotRepository,
)


def cleanup_sandbox_snapshots() -> None:
    """Delete expired sandbox snapshots (systemd timer)."""
    asyncio.run(_cleanup_sandbox_snapshots_async())


async def _cleanup_sandbox_snapshots_async() -> None:
    settings = Settings()
    async with open_session(settings) as session:
        uow = SQLAlchemyUnitOfWork(session)
        snapshots = PostgreSQLSandboxSnapshotRepository(session)
        clock = UTCClock()
        async with uow:
            deleted = await snapshots.delete_expired(now=clock.now())
    typer.echo(f"Cleanup sandbox snapshots complete: deleted={deleted}")
