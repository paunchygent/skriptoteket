from __future__ import annotations

import json

import pytest

from skriptoteket.application.editor.edit_ops_payload_parser import DefaultEditOpsPayloadParser


@pytest.mark.unit
def test_parser_splits_patch_lines_with_embedded_newlines() -> None:
    expected_patch_lines = [
        "diff --git a/tool.py b/tool.py",
        "--- a/tool.py",
        "+++ b/tool.py",
        "@@ -1,1 +1,1 @@",
        "-print('hej')",
        "+print('hello')",
    ]
    payload = {
        "assistant_message": "OK",
        "ops": [
            {
                "op": "patch",
                "target_file": "tool.py",
                "patch_lines": ["\n".join(expected_patch_lines)],
            }
        ],
    }

    raw = "```json\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n```"
    parser = DefaultEditOpsPayloadParser()
    parsed = parser.parse(raw=raw)

    assert parsed is not None
    assert parsed.ops[0].op == "patch"
    assert parsed.ops[0].patch_lines == expected_patch_lines


@pytest.mark.unit
def test_parser_preserves_normal_patch_lines() -> None:
    expected_patch_lines = [
        "diff --git a/tool.py b/tool.py",
        "--- a/tool.py",
        "+++ b/tool.py",
        "@@ -1,1 +1,1 @@",
        "-print('hej')",
        "+print('hello')",
    ]
    payload = {
        "assistant_message": "OK",
        "ops": [
            {
                "op": "patch",
                "target_file": "tool.py",
                "patch_lines": expected_patch_lines,
            }
        ],
    }

    raw = json.dumps(payload)
    parser = DefaultEditOpsPayloadParser()
    parsed = parser.parse(raw=raw)

    assert parsed is not None
    assert parsed.ops[0].patch_lines == expected_patch_lines
