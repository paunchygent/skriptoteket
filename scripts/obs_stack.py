"""Operate the local observability Compose stack from one durable command.

This module keeps Prometheus/Grafana/Jaeger/Loki stack operations behind a
single PDM entrypoint so the script table does not grow one alias per Compose
subcommand.
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

COMPOSE: tuple[str, ...] = ("docker", "compose", "-f", "compose.observability.yaml")

COMMANDS: dict[str, CommandSpec] = {
    "start": CommandSpec(
        summary="Start the observability stack.",
        commands=((*COMPOSE, "up", "-d"),),
    ),
    "stop": CommandSpec(
        summary="Stop the observability stack.",
        commands=((*COMPOSE, "down"),),
    ),
    "restart": CommandSpec(
        summary="Restart the observability stack, or selected services when names are provided.",
        commands=((*COMPOSE, "restart"),),
        accepts_extra_args=True,
    ),
    "logs": CommandSpec(
        summary="Follow observability stack logs, optionally for selected services.",
        commands=((*COMPOSE, "logs", "-f"),),
        accepts_extra_args=True,
    ),
    "status": CommandSpec(
        summary="Show observability stack status.",
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
    return ((*command, *extra_args),)


def main(argv: Sequence[str] | None = None, *, runner: CommandRunner = run_subprocess) -> int:
    return dispatch(
        script_name="obs-stack",
        argv=sys.argv[1:] if argv is None else argv,
        commands=COMMANDS,
        command_builder=_commands_for,
        runner=runner,
    )


if __name__ == "__main__":
    raise SystemExit(main())
