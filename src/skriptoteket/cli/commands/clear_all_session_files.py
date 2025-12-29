from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from skriptoteket.config import Settings
from skriptoteket.infrastructure.clock import UTCClock
from skriptoteket.infrastructure.session_files.local_session_file_storage import (
    LocalSessionFileStorage,
)
from skriptoteket.infrastructure.session_files.usage import get_session_file_usage


def clear_all_session_files(
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompt"),
    artifacts_root: Path | None = typer.Option(None, help="Override ARTIFACTS_ROOT"),
) -> None:
    """Delete all session files under ARTIFACTS_ROOT/sessions/ (DANGER)."""
    settings = Settings()
    effective_root = settings.ARTIFACTS_ROOT if artifacts_root is None else artifacts_root
    sessions_dir = effective_root / "sessions"

    usage = get_session_file_usage(artifacts_root=effective_root)
    if usage.sessions == 0:
        typer.echo(f"No session files found under {sessions_dir}.")
        return

    typer.echo(
        "About to delete ALL session files under "
        f"{sessions_dir} (sessions={usage.sessions}, files={usage.files}, "
        f"bytes_total={usage.bytes_total})."
    )

    if not yes:
        confirmed = typer.confirm("Continue?", default=False)
        if not confirmed:
            raise SystemExit(1)

    asyncio.run(_clear_all_session_files_async(artifacts_root=effective_root))
    typer.echo(f"Deleted all session files under {sessions_dir}.")


async def _clear_all_session_files_async(*, artifacts_root: Path) -> None:
    settings = Settings()
    storage = LocalSessionFileStorage(
        sessions_root=artifacts_root,
        ttl_seconds=settings.SESSION_FILES_TTL_SECONDS,
        clock=UTCClock(),
    )
    await storage.clear_all()
