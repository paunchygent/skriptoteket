"""Operate the Docker Compose development stack from one durable command.

This module is the repo-facing command surface for local Docker development.
It keeps the Compose file pair and the post-start Alembic upgrade step in one
place so `pyproject.toml` does not accumulate one shortcut per Compose flag
combination.
"""

from __future__ import annotations

import sys
from typing import Sequence

from scripts._command_dispatch import (
    CommandRunner,
    CommandSpec,
    dispatch,
    run_subprocess,
)

COMPOSE: tuple[str, ...] = ("docker", "compose", "-f", "compose.yaml", "-f", "compose.dev.yaml")
DB_UPGRADE: tuple[str, ...] = (*COMPOSE, "run", "--rm", "web", "pdm", "run", "db-upgrade")
DEFAULT_LOG_SERVICES: tuple[str, ...] = ("web", "worker", "frontend")


COMMANDS: dict[str, CommandSpec] = {
    "start": CommandSpec(
        summary="Start the Docker dev stack and apply migrations.",
        commands=(
            (*COMPOSE, "up", "-d"),
            DB_UPGRADE,
        ),
    ),
    "web-start": CommandSpec(
        summary="Start Docker db/web for host Vite proof and apply migrations.",
        commands=(
            (*COMPOSE, "up", "-d", "db", "web"),
            DB_UPGRADE,
        ),
    ),
    "stop": CommandSpec(
        summary="Stop the Docker dev stack.",
        commands=((*COMPOSE, "down"),),
    ),
    "restart": CommandSpec(
        summary="Restart the Docker dev stack, or selected services when names are provided.",
        commands=((*COMPOSE, "restart"),),
        accepts_extra_args=True,
    ),
    "recreate": CommandSpec(
        summary=(
            "Force-recreate the Docker dev stack and apply migrations, "
            "or selected services when names are provided."
        ),
        commands=(
            (*COMPOSE, "up", "-d", "--force-recreate"),
            DB_UPGRADE,
        ),
        accepts_extra_args=True,
    ),
    "build-start": CommandSpec(
        summary="Build, start, and apply migrations.",
        commands=(
            (*COMPOSE, "up", "-d", "--build"),
            DB_UPGRADE,
        ),
    ),
    "rebuild": CommandSpec(
        summary="Build, force-recreate, and apply migrations.",
        commands=(
            (*COMPOSE, "up", "-d", "--build", "--force-recreate"),
            DB_UPGRADE,
        ),
    ),
    "build-start-clean": CommandSpec(
        summary="Build without cache, force-recreate, and apply migrations.",
        commands=(
            (*COMPOSE, "build", "--no-cache"),
            (*COMPOSE, "up", "-d", "--force-recreate"),
            DB_UPGRADE,
        ),
    ),
    "db-upgrade": CommandSpec(
        summary="Apply migrations inside the Docker web service.",
        commands=(DB_UPGRADE,),
    ),
    "db-reset": CommandSpec(
        summary="Reset disposable local Docker volumes, start, and apply migrations.",
        commands=(
            (*COMPOSE, "down", "--volumes", "--remove-orphans"),
            (*COMPOSE, "up", "-d"),
            DB_UPGRADE,
        ),
    ),
    "logs": CommandSpec(
        summary="Follow Docker dev logs; defaults to web, worker, and frontend.",
        commands=((*COMPOSE, "logs", "-f", *DEFAULT_LOG_SERVICES),),
        accepts_extra_args=True,
    ),
    "ps": CommandSpec(
        summary="Show Docker dev stack status.",
        commands=((*COMPOSE, "ps"),),
        accepts_extra_args=True,
    ),
}


def _commands_for(
    command_name: str, spec: CommandSpec, extra_args: Sequence[str]
) -> tuple[tuple[str, ...], ...]:
    if not extra_args:
        return spec.commands

    command = spec.commands[0]
    if command_name == "logs":
        return ((*COMPOSE, "logs", "-f", *extra_args),)
    return ((*command, *extra_args),)


def main(argv: Sequence[str] | None = None, *, runner: CommandRunner = run_subprocess) -> int:
    return dispatch(
        script_name="dev-stack",
        argv=sys.argv[1:] if argv is None else argv,
        commands=COMMANDS,
        command_builder=_commands_for,
        runner=runner,
    )


if __name__ == "__main__":
    raise SystemExit(main())
