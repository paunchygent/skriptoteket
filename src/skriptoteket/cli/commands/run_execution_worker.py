from __future__ import annotations

import asyncio

import typer

from skriptoteket.workers.execution_queue_worker import run_execution_queue_worker


def run_execution_worker(
    queue: str = typer.Option("default", help="Queue name to consume from"),
    worker_id: str | None = typer.Option(None, help="Override worker identity"),
    once: bool = typer.Option(False, help="Process at most one job and exit"),
) -> None:
    """Run the Postgres execution-queue worker loop (ADR-0062)."""
    asyncio.run(run_execution_queue_worker(queue=queue, worker_id=worker_id, once=once))
