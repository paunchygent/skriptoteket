from __future__ import annotations

import asyncio
from datetime import timedelta

import typer

from skriptoteket.cli._db import open_session
from skriptoteket.config import Settings
from skriptoteket.infrastructure.clock import UTCClock
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.repositories.login_event_repository import (
    PostgreSQLLoginEventRepository,
)


def cleanup_login_events() -> None:
    """Delete expired login events (systemd timer)."""
    asyncio.run(_cleanup_login_events_async())


async def _cleanup_login_events_async() -> None:
    settings = Settings()
    cutoff = UTCClock().now() - timedelta(days=settings.LOGIN_EVENTS_RETENTION_DAYS)
    async with open_session(settings) as session:
        uow = SQLAlchemyUnitOfWork(session)
        login_events = PostgreSQLLoginEventRepository(session)
        async with uow:
            deleted = await login_events.delete_expired(cutoff=cutoff)
    typer.echo(f"Cleanup login events complete: deleted={deleted}")
