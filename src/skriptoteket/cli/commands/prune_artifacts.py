from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import typer

from skriptoteket.config import Settings
from skriptoteket.infrastructure.runner.retention import prune_artifacts_root


def prune_artifacts(
    retention_days: int | None = typer.Option(None, help="Override ARTIFACTS_RETENTION_DAYS"),
    artifacts_root: Path | None = typer.Option(None, help="Override ARTIFACTS_ROOT"),
    dry_run: bool = typer.Option(False),
) -> None:
    """Delete artifact run directories older than N days (cron-friendly)."""
    settings = Settings()
    effective_root = settings.ARTIFACTS_ROOT if artifacts_root is None else artifacts_root
    effective_days = settings.ARTIFACTS_RETENTION_DAYS if retention_days is None else retention_days

    if dry_run:
        typer.echo(
            "Dry run: would prune artifact directories under "
            f"{effective_root} older than {effective_days} days."
        )
        raise SystemExit(0)

    deleted = prune_artifacts_root(
        artifacts_root=effective_root,
        retention_days=effective_days,
        now=datetime.now(timezone.utc),
    )
    typer.echo(f"Deleted {deleted} artifact run directories from {effective_root}.")
