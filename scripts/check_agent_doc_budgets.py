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
        Budget(path=Path(".agents/handoff.md"), max_lines=200),
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
            "`docs/reference/ref-development-changelog.md`, then keep only current/next-session-critical info here.",
        )

    if not failures:
        return 0

    print("[agent-doc-budgets] Line budget violations:\n")
    for failure in failures:
        print(f"- {failure}")
    print(
        "\nHint: `.agents/handoff.md` is the live session handoff only. "
        "Dump non-session-vital history to repo long-term memory in "
        "`docs/reference/ref-development-changelog.md` before trimming the handoff back under budget.",
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
