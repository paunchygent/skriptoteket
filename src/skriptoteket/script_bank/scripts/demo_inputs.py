"""
Demo: Indata via input_schema (ST-12-04).

Visar hur verktyg kan ta emot text/dropdown-indata via SKRIPTOTEKET_INPUTS och
(valfritt) filer via SKRIPTOTEKET_INPUT_MANIFEST.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def _read_json_env(name: str, *, default: object) -> object:
    raw = os.environ.get(name, "")
    if not raw.strip():
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def run_tool(input_dir: str, output_dir: str) -> dict:
    del input_dir

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    inputs = _read_json_env("SKRIPTOTEKET_INPUTS", default={})
    manifest = _read_json_env("SKRIPTOTEKET_INPUT_MANIFEST", default={"files": []})
    files = manifest.get("files", []) if isinstance(manifest, dict) else []
    if not isinstance(files, list):
        files = []

    inputs_json = json.dumps(inputs, ensure_ascii=False, indent=2)
    (output_root / "inputs.json").write_text(inputs_json, encoding="utf-8")

    file_rows = []
    for item in files:
        if not isinstance(item, dict):
            continue
        file_rows.append(
            {
                "name": item.get("name", ""),
                "path": item.get("path", ""),
                "bytes": item.get("bytes", 0),
            }
        )

    outputs = [
        {
            "kind": "notice",
            "level": "info",
            "message": (
                f"Indata: {len(inputs) if isinstance(inputs, dict) else 0} fält. "
                f"Filer: {len(file_rows)}."
            ),
        },
        {"kind": "json", "title": "SKRIPTOTEKET_INPUTS", "value": inputs},
        {
            "kind": "table",
            "title": "Indatafiler",
            "columns": [
                {"key": "name", "label": "Namn"},
                {"key": "bytes", "label": "Storlek (byte)"},
                {"key": "path", "label": "Sökväg"},
            ],
            "rows": file_rows,
        },
        {
            "kind": "markdown",
            "markdown": "En artefakt `inputs.json` skapas i output_dir.",
        },
    ]

    return {"outputs": outputs, "next_actions": [], "state": None}
