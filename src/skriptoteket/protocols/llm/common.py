"""Shared literal types for LLM protocols."""

from __future__ import annotations

from typing import Literal

SystemMessageVariant = Literal["info", "warning"]
VirtualFileId = Literal[
    "tool.py",
    "entrypoint.txt",
    "settings_schema.json",
    "input_schema.json",
    "usage_instructions.md",
]
