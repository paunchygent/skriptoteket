"""Validate small agent-facing document budgets.

This module backs the repo-local docs validation gate for volatile agent
handoff files. It keeps `.codex/handoff.md` short by directing durable session
history to `.codex/long-term-memory/` and durable policy/procedure to governed
docs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Budget:
    path: Path
    max_lines: int


def _count_lines(*, path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    return len(text.splitlines())


def main() -> int:
    budgets = [
        Budget(path=Path(".codex/handoff.md"), max_lines=200),
    ]

    failures: list[str] = []
    for budget in budgets:
        if not budget.path.exists():
            failures.append(f"Missing required file: {budget.path}")
            continue

        lines = _count_lines(path=budget.path)
        if lines <= budget.max_lines:
            continue

        failures.append(
            f"{budget.path} is {lines} lines (limit: {budget.max_lines}). "
            "Compress non-session-vital handoff content into repo long-term memory at "
            "`.codex/long-term-memory/entries/`, then keep only current-session-critical info here.",
        )

    if not failures:
        return 0

    print("[agent-doc-budgets] Line budget violations:\n")
    for failure in failures:
        print(f"- {failure}")
    print(
        "\nHint: `.codex/handoff.md` is the live session handoff only. "
        "Dump non-session-vital history to repo long-term memory in "
        "`.codex/long-term-memory/entries/` before trimming the handoff back under budget.",
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
