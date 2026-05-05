"""Fast execution-worker dependency healthcheck.

Purpose:
    Provide a Docker healthcheck entrypoint that avoids the heavyweight Typer
    CLI import path used by operator commands.

Relationships:
    - Mirrors the dependency checks in `healthcheck_execution_worker.py`.
    - Used directly from Docker Compose healthchecks for the worker service.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from uuid import uuid4

import asyncpg  # type: ignore[import-untyped]

DB_TIMEOUT_SECONDS = 2.0
DOCKER_TIMEOUT_SECONDS = 3
DEFAULT_ARTIFACTS_ROOT = "/tmp/skriptoteket/artifacts"
ASYNC_SQLALCHEMY_DRIVER_PREFIX = "postgresql+asyncpg://"
POSTGRESQL_PREFIX = "postgresql://"


def main() -> None:
    """Run the worker dependency healthcheck and exit non-zero on failure."""
    try:
        asyncio.run(_run_healthcheck())
    except Exception as exc:  # noqa: BLE001
        print(f"Execution worker healthcheck failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


async def _run_healthcheck() -> None:
    await _check_database(_required_env("DATABASE_URL"))
    _check_docker()
    _check_artifacts(_artifacts_root())


async def _check_database(database_url: str) -> None:
    connection = await asyncpg.connect(
        _asyncpg_database_url(database_url),
        timeout=DB_TIMEOUT_SECONDS,
    )
    try:
        await connection.execute("SELECT 1")
    finally:
        await connection.close()


def _check_docker() -> None:
    import docker

    client = docker.from_env(timeout=DOCKER_TIMEOUT_SECONDS)
    try:
        client.ping()
    finally:
        client.close()


def _check_artifacts(artifacts_root: Path) -> None:
    artifacts_root.mkdir(parents=True, exist_ok=True)
    probe_path = artifacts_root / f".healthcheck-worker-{uuid4()}"
    probe_path.write_text("ok", encoding="utf-8")
    probe_path.unlink(missing_ok=True)


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not configured")
    return value


def _artifacts_root() -> Path:
    return Path(os.environ.get("ARTIFACTS_ROOT", DEFAULT_ARTIFACTS_ROOT))


def _asyncpg_database_url(database_url: str) -> str:
    if database_url.startswith(ASYNC_SQLALCHEMY_DRIVER_PREFIX):
        return f"{POSTGRESQL_PREFIX}{database_url.removeprefix(ASYNC_SQLALCHEMY_DRIVER_PREFIX)}"
    return database_url


if __name__ == "__main__":
    main()
