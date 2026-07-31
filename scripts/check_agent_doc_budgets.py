"""Validate small agent-facing document budgets.

This module backs the repo-local docs validation gate for volatile agent
handoff files. It keeps `handoff.md` short by directing durable session
history to `.codex/long-term-memory/` and durable policy/procedure to governed
docs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

LTM_ENTRIES_DIR = Path(".codex/long-term-memory/entries")
LTM_ENTRY_FILENAME_PREFIX = "session-"


@dataclass(frozen=True, slots=True)
class Budget:
    path: Path
    max_lines: int


def _count_lines(*, path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    return len(text.splitlines())


def main() -> int:
    budgets = [
        Budget(path=Path("handoff.md"), max_lines=200),
    ]

    failures: list[str] = []
    if LTM_ENTRIES_DIR.exists():
        for entry in sorted(LTM_ENTRIES_DIR.glob("*.md")):
            if not entry.name.startswith(LTM_ENTRY_FILENAME_PREFIX):
                failures.append(
                    f"{entry}: long-term-memory entries must use session-*.md filenames. "
                    "Rename the entry and update .codex/long-term-memory/index.md.",
                )

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
        "\nHint: `handoff.md` is the live session handoff only. "
        "Dump non-session-vital history to repo long-term memory in "
        "`.codex/long-term-memory/entries/` before trimming the handoff back under budget.",
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
