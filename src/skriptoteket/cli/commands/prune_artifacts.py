from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import typer

from skriptoteket.config import Settings
from skriptoteket.infrastructure.runner.retention import (
    prune_artifacts_root,
    prune_llm_captures_root,
)


def prune_artifacts(
    retention_days: int | None = typer.Option(None, help="Override ARTIFACTS_RETENTION_DAYS"),
    artifacts_root: Path | None = typer.Option(None, help="Override ARTIFACTS_ROOT"),
    dry_run: bool = typer.Option(False),
) -> None:
    """Delete artifact run directories and LLM captures older than N days (cron-friendly)."""
    settings = Settings()
    effective_root = settings.ARTIFACTS_ROOT if artifacts_root is None else artifacts_root
    effective_days = settings.ARTIFACTS_RETENTION_DAYS if retention_days is None else retention_days

    if dry_run:
        typer.echo(
            "Dry run: would prune artifact directories and LLM captures under "
            f"{effective_root} older than {effective_days} days."
        )
        raise SystemExit(0)

    now = datetime.now(timezone.utc)
    deleted_runs = prune_artifacts_root(
        artifacts_root=effective_root,
        retention_days=effective_days,
        now=now,
    )
    deleted_llm_captures = prune_llm_captures_root(
        artifacts_root=effective_root,
        retention_days=effective_days,
        now=now,
    )
    llm_captures_root = effective_root / "llm-captures"
    typer.echo(f"Deleted {deleted_runs} artifact run directories from {effective_root}.")
    typer.echo(f"Deleted {deleted_llm_captures} LLM capture directories from {llm_captures_root}.")
