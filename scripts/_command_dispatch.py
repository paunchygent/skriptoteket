"""Shared command-dispatch helpers for repo-local operator scripts.

The helpers keep small PDM-facing operator modules focused on declaring their
subcommands while preserving a consistent CLI shape and failure behavior.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Protocol, Sequence


class CommandRunner(Protocol):
    """Run one command and return its process exit code."""

    def __call__(self, command: Sequence[str]) -> int:
        """Execute a command."""


@dataclass(frozen=True, slots=True)
class CommandSpec:
    """Describe one operator subcommand."""

    summary: str
    commands: tuple[tuple[str, ...], ...]
    accepts_extra_args: bool = False


def run_subprocess(command: Sequence[str]) -> int:
    """Run a subprocess without raising on non-zero exit."""
    return subprocess.run(command, check=False).returncode


def usage(*, script_name: str, commands: dict[str, CommandSpec]) -> str:
    """Build a stable help message for a subcommand dispatcher."""
    rows = "\n".join(f"  {name:<18} {spec.summary}" for name, spec in commands.items())
    return f"Usage: pdm run {script_name} <command> [args]\n\nCommands:\n{rows}"


def dispatch(
    *,
    script_name: str,
    argv: Sequence[str],
    commands: dict[str, CommandSpec],
    command_builder,
    runner: CommandRunner = run_subprocess,
) -> int:
    """Dispatch a subcommand and stop on the first failed process."""
    args = list(argv)
    help_text = usage(script_name=script_name, commands=commands)
    if not args or args[0] in {"-h", "--help", "help"}:
        print(help_text)
        return 0

    command_name = args[0]
    if command_name not in commands:
        print(f"Unknown {script_name} command: {command_name}\n\n{help_text}")
        return 2

    spec = commands[command_name]
    extra_args = args[1:]
    if extra_args and not spec.accepts_extra_args:
        print(f"`{command_name}` does not accept extra arguments.\n\n{help_text}")
        return 2

    for command in command_builder(command_name, spec, extra_args):
        code = runner(command)
        if code != 0:
            return code
    return 0
