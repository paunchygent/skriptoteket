"""Structured-output format for editor chat ops (patch-only edit operations)."""

from __future__ import annotations

from pydantic import JsonValue

from skriptoteket.infrastructure.llm.openai.types import ResponsesJsonSchemaTextFormat

_EDIT_OPS_PATCH_ONLY_SCHEMA: dict[str, JsonValue] = {
    "type": "object",
    "properties": {
        "assistant_message": {"type": "string"},
        "ops": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "op": {"type": "string", "enum": ["patch"]},
                    "target_file": {
                        "type": "string",
                        "enum": [
                            "tool.py",
                            "entrypoint.txt",
                            "settings_schema.json",
                            "input_schema.json",
                            "usage_instructions.md",
                        ],
                    },
                    "patch_lines": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["op", "target_file", "patch_lines"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["assistant_message", "ops"],
    "additionalProperties": False,
}

EDIT_OPS_PATCH_ONLY_RESPONSES_TEXT_FORMAT: ResponsesJsonSchemaTextFormat = {
    "type": "json_schema",
    "name": "edit_ops_patch_only",
    "schema": _EDIT_OPS_PATCH_ONLY_SCHEMA,
}
