"""
Demo: Personalized tool settings test.

Purpose:
- Dedicated tool for Playwright E2E test (ST-12-03)
- Tests settings persistence: settings_schema → memory.json → runner injection
- Isolates test from demo-next-actions to prevent source code pollution

Runner contract:
- Entrypoint: run_tool(input_dir: str, output_dir: str) -> dict
- Reads settings from SKRIPTOTEKET_MEMORY_PATH environment variable
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def run_tool(input_dir: str, output_dir: str) -> dict:
    """Read settings from memory and output them for verification."""
    memory_path = os.environ.get("SKRIPTOTEKET_MEMORY_PATH", "/work/memory.json")
    try:
        memory = json.loads(Path(memory_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        memory = {}

    settings = memory.get("settings", {}) if isinstance(memory, dict) else {}
    theme_color = settings.get("theme_color", "")

    return {
        "outputs": [
            {"kind": "notice", "level": "info", "message": f"theme_color={theme_color}"},
            {"kind": "json", "title": "settings", "value": settings},
        ],
        "next_actions": [],
        "state": None,
    }
