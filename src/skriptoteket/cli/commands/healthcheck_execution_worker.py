from __future__ import annotations

import asyncio
from uuid import uuid4

import typer
from sqlalchemy import text

from skriptoteket.cli._db import open_session
from skriptoteket.config import Settings


def healthcheck_execution_worker() -> None:
    """Healthcheck for the execution worker container.

    Intended for Docker Compose healthcheck usage.
    """
    asyncio.run(_healthcheck_execution_worker_async())


async def _healthcheck_execution_worker_async() -> None:
    settings = Settings()

    try:
        async with open_session(settings) as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"DB healthcheck failed: {exc}")
        raise typer.Exit(code=1) from exc

    try:
        import docker

        docker.from_env(timeout=3).ping()
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"Docker healthcheck failed: {exc}")
        raise typer.Exit(code=1) from exc

    try:
        artifacts_root = settings.ARTIFACTS_ROOT
        artifacts_root.mkdir(parents=True, exist_ok=True)
        probe_path = artifacts_root / f".healthcheck-worker-{uuid4()}"
        probe_path.write_text("ok", encoding="utf-8")
        probe_path.unlink(missing_ok=True)
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"Artifacts healthcheck failed: {exc}")
        raise typer.Exit(code=1) from exc
