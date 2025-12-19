from __future__ import annotations

import json
import os
import sys
import traceback
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Literal, TypedDict


class RunnerArtifact(TypedDict):
    path: str
    bytes: int


JsonPrimitive = str | int | float | bool | None
JsonValue = JsonPrimitive | dict[str, "JsonValue"] | list["JsonValue"]
RunnerUiObject = dict[str, JsonValue]

RunnerStatus = Literal["succeeded", "failed", "timed_out"]


class RunnerResultPayloadV2(TypedDict):
    contract_version: Literal[2]
    status: RunnerStatus
    error_summary: str | None
    outputs: list[RunnerUiObject]
    next_actions: list[RunnerUiObject]
    state: dict[str, JsonValue] | None
    artifacts: list[RunnerArtifact]


def _stable_json_sort_key(value: JsonValue) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _to_json_value(value: object, *, depth: int = 0, max_depth: int = 50) -> JsonValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if depth >= max_depth:
        return str(value)

    if isinstance(value, dict):
        result: dict[str, JsonValue] = {}
        for key, raw in value.items():
            if not isinstance(key, str):
                continue
            result[key] = _to_json_value(raw, depth=depth + 1, max_depth=max_depth)
        return result

    if isinstance(value, (list, tuple)):
        return [_to_json_value(item, depth=depth + 1, max_depth=max_depth) for item in value]

    if isinstance(value, (set, frozenset)):
        converted = [_to_json_value(item, depth=depth + 1, max_depth=max_depth) for item in value]
        converted.sort(key=_stable_json_sort_key)
        return converted

    return str(value)


def _coerce_ui_object(value: object) -> RunnerUiObject | None:
    if not isinstance(value, dict):
        return None
    json_value = _to_json_value(value)
    if isinstance(json_value, dict):
        return json_value
    return None


def _coerce_ui_object_list(value: object) -> list[RunnerUiObject]:
    if not isinstance(value, list):
        return []
    result: list[RunnerUiObject] = []
    for item in value:
        obj = _coerce_ui_object(item)
        if obj is not None:
            result.append(obj)
    return result


def _coerce_state(value: object) -> dict[str, JsonValue] | None:
    if value is None:
        return None
    json_value = _to_json_value(value)
    if isinstance(json_value, dict):
        return json_value
    return None


def _to_contract_v2_ui_fields(
    result: object,
) -> tuple[list[RunnerUiObject], list[RunnerUiObject], dict[str, JsonValue] | None]:
    """Convert a script return value into contract v2 UI fields.

    Supported tool return shapes:
    - str: treated as a single `html_sandboxed` output (backwards compatible)
    - dict: treated as a partial contract payload containing optional `outputs`, `next_actions`,
      and `state`
    """

    if isinstance(result, str):
        html = result
        outputs: list[RunnerUiObject] = []
        if html:
            outputs.append({"kind": "html_sandboxed", "html": html})
        return outputs, [], None

    if isinstance(result, dict):
        outputs = _coerce_ui_object_list(result.get("outputs"))
        next_actions = _coerce_ui_object_list(result.get("next_actions"))
        state = _coerce_state(result.get("state"))
        return outputs, next_actions, state

    raise TypeError("Entrypoint must return a str (HTML) or a dict (contract v2 payload)")


def _load_module_from_path(*, module_path: Path) -> object:
    spec = spec_from_file_location("tool_script", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load tool script (invalid spec)")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _safe_error_summary(*, error: BaseException) -> str:
    return f"Tool execution failed ({type(error).__name__})."


def _collect_artifacts(*, work_dir: Path, output_dir: Path) -> list[RunnerArtifact]:
    artifacts: list[RunnerArtifact] = []
    for file_path in output_dir.rglob("*"):
        if not file_path.is_file():
            continue
        relative_to_work = file_path.relative_to(work_dir).as_posix()
        artifacts.append({"path": relative_to_work, "bytes": file_path.stat().st_size})
    artifacts.sort(key=lambda a: a["path"])
    return artifacts


def main() -> int:
    work_dir = Path("/work")

    script_path = Path(os.getenv("SKRIPTOTEKET_SCRIPT_PATH", "/work/script.py"))
    entrypoint = os.getenv("SKRIPTOTEKET_ENTRYPOINT", "run_tool").strip()
    input_path = Path(os.getenv("SKRIPTOTEKET_INPUT_PATH", "/work/input"))
    output_dir = Path(os.getenv("SKRIPTOTEKET_OUTPUT_DIR", "/work/output"))
    result_path = Path(os.getenv("SKRIPTOTEKET_RESULT_PATH", "/work/result.json"))

    status: RunnerStatus = "failed"
    error_summary: str | None = None
    artifacts: list[RunnerArtifact] = []
    outputs: list[RunnerUiObject] = []
    next_actions: list[RunnerUiObject] = []
    state: dict[str, JsonValue] | None = None

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        module = _load_module_from_path(module_path=script_path)

        func = getattr(module, entrypoint, None)
        if func is None or not callable(func):
            raise RuntimeError(f"Entrypoint not found: {entrypoint}")

        result = func(str(input_path), str(output_dir))

        outputs, next_actions, state = _to_contract_v2_ui_fields(result)
        status = "succeeded"
        artifacts = _collect_artifacts(work_dir=work_dir, output_dir=output_dir)

    except BaseException as e:  # noqa: BLE001 - runner boundary; writes a safe result.json
        error_summary = _safe_error_summary(error=e)
        traceback.print_exc(file=sys.stderr)

    payload: RunnerResultPayloadV2 = {
        "contract_version": 2,
        "status": status,
        "error_summary": error_summary,
        "outputs": outputs,
        "next_actions": next_actions,
        "state": state,
        "artifacts": artifacts,
    }
    result_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
