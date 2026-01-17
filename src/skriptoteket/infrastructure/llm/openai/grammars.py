from __future__ import annotations

_EDIT_OPS_PATCH_ONLY_GBNF_LINES = [
    "root ::= editops",
    "",
    'editops ::= "{" ws "\\"assistant_message\\"" ws ":" ws string "," ws '
    '"\\"ops\\"" ws ":" ws opsarray "}" ws',
    "",
    'opsarray ::= "[" ws (patchop ("," ws patchop)*)? "]" ws',
    "",
    'patchop ::= "{" ws "\\"op\\"" ws ":" ws "\\"patch\\"" ws "," ws '
    '"\\"target_file\\"" ws ":" ws fileid ws "," ws '
    '"\\"patch_lines\\"" ws ":" ws stringarray "}" ws',
    "",
    'fileid ::= "\\"tool.py\\"" | "\\"entrypoint.txt\\"" | '
    '"\\"settings_schema.json\\"" | "\\"input_schema.json\\"" | '
    '"\\"usage_instructions.md\\""',
    "",
    'stringarray ::= "[" ws (string ("," ws string)*)? "]" ws',
    "",
    'string ::= "\\"" (',
    '  [^"\\\\\\x7F\\x00-\\x1F] |',
    '  "\\\\" (["\\\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F]) # escapes',
    ')* "\\"" ws',
    "",
    "# Optional space: by convention, applied in this grammar after literal chars when allowed",
    "ws ::= ([ \\t\\n] ws)?",
]

EDIT_OPS_PATCH_ONLY_GBNF = "\n".join(_EDIT_OPS_PATCH_ONLY_GBNF_LINES).strip()

EDIT_OPS_PATCH_ONLY_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "edit_ops_patch_only",
        "schema": {
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
        },
    },
}
