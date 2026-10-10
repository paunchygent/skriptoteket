from __future__ import annotations

from typing import NotRequired, TypeAlias, TypedDict

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | dict[str, JsonValue] | list[JsonValue]

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

def read_inputs() -> dict[str, JsonValue]: ...
def read_input_manifest() -> dict[str, JsonValue]: ...
def list_input_files() -> list[ManifestFile]: ...
def read_action() -> ActionPayload | None: ...
def get_action_parts() -> tuple[str | None, dict[str, JsonValue], dict[str, JsonValue]]: ...
def read_memory() -> dict[str, JsonValue]: ...
def read_settings() -> dict[str, JsonValue]: ...
