from __future__ import annotations

import asyncio
from datetime import timedelta
from uuid import UUID

import typer

from skriptoteket.cli._db import open_session
from skriptoteket.config import Settings
from skriptoteket.infrastructure.clock import UTCClock
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.repositories.user_vault_file_repository import (
    PostgreSQLUserVaultFileRepository,
)
from skriptoteket.infrastructure.repositories.user_vault_usage_repository import (
    PostgreSQLUserVaultUsageRepository,
)
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage


def cleanup_vault_files() -> None:
    """Delete expired vault files past retention (cron-friendly)."""
    asyncio.run(_cleanup_vault_files_async())


async def _cleanup_vault_files_async() -> None:
    settings = Settings()
    if settings.VAULT_RETENTION_DAYS < 0:
        raise ValueError("VAULT_RETENTION_DAYS must be >= 0")

    clock = UTCClock()
    now = clock.now()
    cutoff = now - timedelta(days=settings.VAULT_RETENTION_DAYS)

    async with open_session(settings) as session:
        uow = SQLAlchemyUnitOfWork(session)
        vault_files = PostgreSQLUserVaultFileRepository(session)
        vault_usage = PostgreSQLUserVaultUsageRepository(session)
        storage = LocalVaultStorage(vault_root=settings.VAULT_ROOT)

        deleted = 0
        affected_users: set[UUID] = set()

        async with uow:
            while True:
                expired = await vault_files.list_expired(cutoff=cutoff, limit=200)
                if not expired:
                    break
                for item in expired:
                    await storage.delete_file(user_id=item.user_id, file_id=item.id)
                    await vault_files.delete(file_id=item.id)
                    deleted += 1
                    affected_users.add(item.user_id)

            for user_id in affected_users:
                await vault_usage.recompute_total(user_id=user_id, now=now)

    typer.echo(f"Cleanup vault files complete: deleted={deleted}")
