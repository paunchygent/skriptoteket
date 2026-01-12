from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, TypedDict

JsonPrimitive = str | int | float | bool | None
JsonValue = JsonPrimitive | dict[str, "JsonValue"] | list["JsonValue"]


class ManifestFile(TypedDict):
    name: str
    path: str
    bytes: int


class ActionPayload(TypedDict):
    action_id: str
    input: dict[str, JsonValue]
    state: dict[str, JsonValue]


def _read_json_env(name: str) -> object | None:
    raw = os.environ.get(name, "")
    if not raw.strip():
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _read_json_file(path: Path) -> object | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def read_inputs() -> dict[str, JsonValue]:
    """Parse SKRIPTOTEKET_INPUTS (JSON object). Returns {} on missing/invalid JSON."""
    payload = _read_json_env("SKRIPTOTEKET_INPUTS")
    return payload if isinstance(payload, dict) else {}


def read_input_manifest() -> dict[str, Any]:
    """Parse SKRIPTOTEKET_INPUT_MANIFEST (JSON). Returns {"files": []} on missing/invalid JSON."""
    payload = _read_json_env("SKRIPTOTEKET_INPUT_MANIFEST")
    if isinstance(payload, dict):
        return payload
    return {"files": []}


def list_input_files() -> list[ManifestFile]:
    """Return validated files from SKRIPTOTEKET_INPUT_MANIFEST. Returns [] on missing/invalid."""
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
        if isinstance(bytes_, bool):
            continue
        if isinstance(name, str) and isinstance(path, str) and isinstance(bytes_, int):
            files.append({"name": name, "path": path, "bytes": bytes_})
    return files


def read_action() -> ActionPayload | None:
    """Parse SKRIPTOTEKET_ACTION.

    Returns None if missing or malformed.
    """
    payload = _read_json_env("SKRIPTOTEKET_ACTION")
    if not isinstance(payload, dict):
        return None

    action_id = payload.get("action_id")
    if not isinstance(action_id, str):
        return None
    action_id = action_id.strip()
    if not action_id:
        return None

    raw_input = payload.get("input")
    input_value = raw_input if isinstance(raw_input, dict) else {}

    raw_state = payload.get("state")
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
