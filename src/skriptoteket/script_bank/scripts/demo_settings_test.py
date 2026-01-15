"""
Demo: Personalized tool settings test.

Purpose:
- Dedicated tool for Playwright E2E test (ST-12-03)
- Tests settings persistence: settings_schema → memory.json → runner injection
- Isolates test from demo-next-actions to prevent source code pollution

Runner contract:
- Entrypoint: run_tool(input_dir: str, output_dir: str) -> dict
- Reads settings via `skriptoteket_toolkit.read_settings()` (memory.json injected by the platform)
"""

from __future__ import annotations

from skriptoteket_toolkit import read_settings  # type: ignore[import-not-found]


def run_tool(input_dir: str, output_dir: str) -> dict:
    """Read settings from memory and output them for verification."""
    settings = read_settings()
    theme_color = settings.get("theme_color", "")

    return {
        "outputs": [
            {"kind": "notice", "level": "info", "message": f"theme_color={theme_color}"},
            {"kind": "json", "title": "settings", "value": settings},
        ],
        "next_actions": [],
        "state": None,
    }
