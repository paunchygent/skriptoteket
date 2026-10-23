"""Validate long-term-memory entry filenames.

`handoff.md` itself is validated by the shared `handoff-validate` command.
This module checks that retained session-history entries under
`.codex/long-term-memory/entries/` use `session-*.md` filenames.
"""

from __future__ import annotations

from pathlib import Path

LTM_ENTRIES_DIR = Path(".codex/long-term-memory/entries")
LTM_ENTRY_FILENAME_PREFIX = "session-"


def main() -> int:
    failures: list[str] = []
    if LTM_ENTRIES_DIR.exists():
        for entry in sorted(LTM_ENTRIES_DIR.glob("*.md")):
            if not entry.name.startswith(LTM_ENTRY_FILENAME_PREFIX):
                failures.append(
                    f"{entry}: long-term-memory entries must use session-*.md filenames. "
                    "Rename the entry and update .codex/long-term-memory/index.md.",
                )

    if not failures:
        return 0

    print("[long-term-memory-entries] Filename violations:\n")
    for failure in failures:
        print(f"- {failure}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
