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
        Budget(path=Path(".agent/readme-first.md"), max_lines=300),
        Budget(path=Path(".agent/handoff.md"), max_lines=200),
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
            "Prune old/completed content; move history to docs/ and keep only current sprint-critical info.",
        )

    if not failures:
        return 0

    print("[agent-doc-budgets] Line budget violations:\n")
    for failure in failures:
        print(f"- {failure}")
    print(
        "\nHint: `.agent/handoff.md` should only keep last critical backend+frontend session + current/next session; "
        "move completed stories to `.agent/readme-first.md` as links only.",
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

