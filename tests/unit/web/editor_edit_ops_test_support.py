"""Shared helpers for editor edit-ops route tests.

Purpose:
    Build the virtual-file payload the edit-ops routes accept.

Relationships:
    - Used by `test_editor_edit_ops_generation_api.py` and
      `test_editor_edit_ops_preview_apply_api.py`; their app fixtures live in
      `tests.fixtures.editor_edit_ops_api_app`.
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
