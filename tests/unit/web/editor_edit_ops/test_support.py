"""Shared helpers for editor edit-ops route tests.

Purpose:
    Build the virtual-file payload the edit-ops routes accept.

Relationships:
    - Used by `test_generation_api.py` and `test_preview_apply_api.py`; their
      app fixtures live in `conftest.py` in this directory.
"""

from __future__ import annotations


def virtual_files(tool_py: str) -> dict[str, str]:
    return {
        "tool.py": tool_py,
        "entrypoint.txt": "run_tool\n",
        "settings_schema.json": "{}",
        "input_schema.json": "{}",
        "usage_instructions.md": "",
    }
