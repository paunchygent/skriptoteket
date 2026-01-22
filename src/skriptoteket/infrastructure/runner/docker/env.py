import json
from dataclasses import dataclass

from pydantic import JsonValue

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.input_files import normalize_input_files
from skriptoteket.domain.scripting.models import ToolVersion


@dataclass(frozen=True, slots=True)
class ExecutionInputs:
    env: dict[str, str]
    normalized_input_files: list[tuple[str, bytes]]
    input_manifest_json: str
    inputs_json: str


def prepare_execution_inputs(
    *,
    version: ToolVersion,
    input_files: list[tuple[str, bytes]],
    input_values: dict[str, JsonValue],
    action_payload: dict[str, JsonValue] | None,
) -> ExecutionInputs:
    normalized_input_files = (
        normalize_input_files(input_files=input_files)[0] if input_files else []
    )
    input_manifest = {
        "files": [
            {"name": name, "path": f"/work/input/{name}", "bytes": len(content)}
            for name, content in normalized_input_files
        ]
    }
    input_manifest_json = json.dumps(input_manifest, ensure_ascii=False, separators=(",", ":"))
    inputs_json = json.dumps(input_values, ensure_ascii=False, separators=(",", ":"))

    env: dict[str, str] = {
        "HOME": "/tmp/home",
        "XDG_CACHE_HOME": "/tmp/home/.cache",
        "SKRIPTOTEKET_SCRIPT_PATH": "/work/script.py",
        "SKRIPTOTEKET_ENTRYPOINT": version.entrypoint,
        "SKRIPTOTEKET_INPUT_DIR": "/work/input",
        "SKRIPTOTEKET_INPUT_MANIFEST": input_manifest_json,
        "SKRIPTOTEKET_INPUTS": inputs_json,
        "SKRIPTOTEKET_MEMORY_PATH": "/work/memory.json",
        "SKRIPTOTEKET_OUTPUT_DIR": "/work/output",
        "SKRIPTOTEKET_RESULT_PATH": "/work/result.json",
    }
    if action_payload is not None:
        try:
            env["SKRIPTOTEKET_ACTION"] = json.dumps(
                action_payload,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        except TypeError as exc:
            raise DomainError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Failed to encode action payload as JSON.",
            ) from exc

    return ExecutionInputs(
        env=env,
        normalized_input_files=normalized_input_files,
        input_manifest_json=input_manifest_json,
        inputs_json=inputs_json,
    )
