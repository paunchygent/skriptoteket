from __future__ import annotations

import json
import os
from pathlib import Path
from typing import NotRequired, TypedDict

"""Stable helper API for Skriptoteket tool scripts (runner environment).

Tool scripts run inside the isolated runner container. The platform injects a request
payload via `/work/request.json` and settings via memory JSON.

Prefer these helpers instead of reading/parsing `os.environ` directly:

- Predictable defaults on missing/malformed JSON (no crashes).
- A small, stable API surface that can be referenced by editor intelligence and AI assistants.

Typical usage:

```py
from pathlib import Path
from skriptoteket_toolkit import get_action_parts, list_input_files, read_inputs, read_settings

action_id, action_input, state = get_action_parts()
inputs = action_input if action_id else read_inputs()
settings = read_settings()
files = [Path(f["path"]) for f in list_input_files()]
```
"""

JsonPrimitive = str | int | float | bool | None
JsonValue = JsonPrimitive | dict[str, "JsonValue"] | list["JsonValue"]

__all__ = [
    "ActionPayload",
    "JsonValue",
    "ManifestFile",
    "get_action_parts",
    "list_input_files",
    "read_action",
    "read_input_manifest",
    "read_inputs",
    "read_memory",
    "read_settings",
]


class ManifestFile(TypedDict):
    name: str
    path: str
    bytes: int
    ref: NotRequired[str | None]
    field: NotRequired[str]


class ActionPayload(TypedDict):
    action_id: str
    input: dict[str, JsonValue]
    state: dict[str, JsonValue]


def _read_json_file(path: Path) -> object | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _read_request_payload() -> dict[str, JsonValue] | None:
    payload = _read_json_file(Path("/work/request.json"))
    return payload if isinstance(payload, dict) else None


def read_inputs() -> dict[str, JsonValue]:
    """Parse request.json inputs.values. Returns {} on missing/invalid JSON."""
    payload = _read_request_payload()
    if payload is None:
        return {}
    raw_inputs = payload.get("inputs")
    if not isinstance(raw_inputs, dict):
        return {}
    raw_values = raw_inputs.get("values")
    return raw_values if isinstance(raw_values, dict) else {}


def read_input_manifest() -> dict[str, JsonValue]:
    """Parse request.json files. Returns {"files": []} on missing/invalid JSON."""
    payload = _read_request_payload()
    if payload is None:
        return {"files": []}
    raw_files = payload.get("files")
    return {"files": raw_files} if isinstance(raw_files, list) else {"files": []}


def list_input_files() -> list[ManifestFile]:
    """Return validated files from request.json manifest. Returns [] on missing/invalid."""
    manifest = read_input_manifest()
    raw_files = manifest.get("files")
    if not isinstance(raw_files, list):
        return []

    files: list[ManifestFile] = []
    for item in raw_files:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        path = item.get("path")
        bytes_ = item.get("bytes")
        ref = item.get("ref")
        field = item.get("field")
        if isinstance(bytes_, bool):
            continue
        if isinstance(name, str) and isinstance(path, str) and isinstance(bytes_, int):
            entry: ManifestFile = {"name": name, "path": path, "bytes": bytes_}
            if isinstance(ref, str):
                entry["ref"] = ref
            if isinstance(field, str) and field.strip():
                entry["field"] = field
            files.append(entry)
    return files


def read_action() -> ActionPayload | None:
    """Parse request.json action payload. Returns None if missing or malformed."""
    payload = _read_request_payload()
    if payload is None:
        return None

    raw_action = payload.get("action")
    if not isinstance(raw_action, dict):
        return None

    action_id = raw_action.get("action_id")
    if not isinstance(action_id, str):
        return None
    action_id = action_id.strip()
    if not action_id:
        return None

    raw_input = raw_action.get("input")
    input_value = raw_input if isinstance(raw_input, dict) else {}

    raw_state = raw_action.get("state")
    state_value = raw_state if isinstance(raw_state, dict) else {}

    return {
        "action_id": action_id,
        "input": input_value,
        "state": state_value,
    }


def get_action_parts() -> tuple[str | None, dict[str, JsonValue], dict[str, JsonValue]]:
    """Return (action_id, input, state) with predictable defaults.

    - If not an action run: (None, {}, {})
    - If malformed: (None, {}, {})
    """
    action = read_action()
    if action is None:
        return None, {}, {}
    return action["action_id"], action["input"], action["state"]


def read_memory() -> dict[str, JsonValue]:
    """Parse memory JSON from SKRIPTOTEKET_MEMORY_PATH. Returns {} on missing/invalid."""
    raw_path = os.environ.get("SKRIPTOTEKET_MEMORY_PATH", "").strip()
    if not raw_path:
        return {}
    payload = _read_json_file(Path(raw_path))
    return payload if isinstance(payload, dict) else {}


def read_settings() -> dict[str, JsonValue]:
    """Return memory['settings'] (dict) or {}."""
    memory = read_memory()
    settings = memory.get("settings")
    return settings if isinstance(settings, dict) else {}
