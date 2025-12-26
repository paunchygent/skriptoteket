from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_META_FILENAME = "meta.json"


@dataclass(frozen=True)
class SessionFileUsage:
    sessions: int
    files: int
    bytes_total: int


def get_session_file_usage(*, artifacts_root: Path) -> SessionFileUsage:
    sessions_dir = artifacts_root / "sessions"
    if not sessions_dir.exists():
        return SessionFileUsage(sessions=0, files=0, bytes_total=0)

    sessions = 0
    files = 0
    bytes_total = 0

    for tool_dir in sessions_dir.iterdir():
        if not tool_dir.is_dir():
            continue
        for user_dir in tool_dir.iterdir():
            if not user_dir.is_dir():
                continue
            for context_dir in user_dir.iterdir():
                if not context_dir.is_dir():
                    continue

                sessions += 1
                for item in context_dir.iterdir():
                    if item.name == _META_FILENAME:
                        continue
                    if not item.is_file():
                        continue
                    files += 1
                    try:
                        bytes_total += item.stat().st_size
                    except OSError:
                        pass

    return SessionFileUsage(sessions=sessions, files=files, bytes_total=bytes_total)
