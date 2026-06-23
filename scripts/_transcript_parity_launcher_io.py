"""Transcript parity launcher subprocess helpers.

Domain purpose:
    Provide the command execution boundary used by the Audio Transcription
    parity proof launcher so orchestration logic can stay focused on lane
    descriptors and runtime validation.

Relationships:
    Imported by `scripts.transcript_parity_proof_launcher` and its focused unit
    tests to keep subprocess construction injectable and side-effect free.
"""

from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Completed command result returned by launcher command executors."""

    returncode: int
    stdout: str
    stderr: str


class CommandExecutor(Protocol):
    """Run one command for the launcher."""

    def __call__(
        self,
        command: Sequence[str],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        timeout_seconds: int | None = None,
    ) -> CommandResult:
        """Execute a subprocess and return bounded process output."""


def run_subprocess(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    timeout_seconds: int | None = None,
) -> CommandResult:
    """Run one subprocess and capture output without echoing secrets or tokens."""

    completed = subprocess.run(
        list(command),
        cwd=cwd,
        env=dict(env) if env is not None else None,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
