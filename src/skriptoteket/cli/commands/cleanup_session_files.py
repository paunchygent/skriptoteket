from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from skriptoteket.config import Settings
from skriptoteket.infrastructure.clock import UTCClock
from skriptoteket.infrastructure.session_files.local_session_file_storage import (
    LocalSessionFileStorage,
)


def cleanup_session_files(
    artifacts_root: Path | None = typer.Option(None, help="Override ARTIFACTS_ROOT"),
) -> None:
    """Delete expired session file directories based on TTL (cron-friendly)."""
    asyncio.run(_cleanup_session_files_async(artifacts_root=artifacts_root))


async def _cleanup_session_files_async(*, artifacts_root: Path | None) -> None:
    settings = Settings()
    effective_root = settings.ARTIFACTS_ROOT if artifacts_root is None else artifacts_root
    storage = LocalSessionFileStorage(
        sessions_root=effective_root,
        ttl_seconds=settings.SESSION_FILES_TTL_SECONDS,
        clock=UTCClock(),
    )
    result = await storage.cleanup_expired()
    typer.echo(
        "Cleanup session files complete: "
        f"scanned_sessions={result.scanned_sessions} "
        f"deleted_sessions={result.deleted_sessions} "
        f"deleted_files={result.deleted_files} "
        f"deleted_bytes={result.deleted_bytes} "
        f"artifacts_root={effective_root}"
    )
