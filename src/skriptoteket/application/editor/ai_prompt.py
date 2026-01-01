from __future__ import annotations

from functools import lru_cache
from pathlib import Path


def _resolve_prompt_path(*, prompt_path: str) -> Path:
    resolved = Path(prompt_path)
    if resolved.is_absolute():
        return resolved

    # Repo layout: <root>/src/skriptoteket/application/editor/ai_prompt.py
    root = Path(__file__).resolve().parents[4]
    return root / resolved


@lru_cache(maxsize=4)
def load_system_prompt_text(*, prompt_path: str) -> str:
    path = _resolve_prompt_path(prompt_path=prompt_path)
    return path.read_text(encoding="utf-8")
