"""Operator entrypoint for the canonical native worker dependency check."""

from skriptoteket.cli.commands.healthcheck_execution_worker_fast import main


def healthcheck_execution_worker() -> None:
    """Run the worker dependency check and propagate its exit status."""
    main()
