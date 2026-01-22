from dataclasses import dataclass
from typing import Protocol

from pydantic import JsonValue

from skriptoteket.domain.scripting.models import ToolVersion

from .env import prepare_execution_inputs
from .workdir_archive import build_workdir_archive


@dataclass(frozen=True, slots=True)
class RunnerRequest:
    env: dict[str, str]
    normalized_input_files: list[tuple[str, bytes]]
    input_manifest_json: str
    inputs_json: str
    request_json_bytes: bytes | None
    workdir_archive: bytes


class RunnerRequestFactoryProtocol(Protocol):
    def build_request(
        self,
        *,
        version: ToolVersion,
        input_files: list[tuple[str, bytes]],
        input_values: dict[str, JsonValue],
        memory_json: bytes,
        action_payload: dict[str, JsonValue] | None,
    ) -> RunnerRequest: ...


class V2RunnerRequestFactory:
    def build_request(
        self,
        *,
        version: ToolVersion,
        input_files: list[tuple[str, bytes]],
        input_values: dict[str, JsonValue],
        memory_json: bytes,
        action_payload: dict[str, JsonValue] | None,
    ) -> RunnerRequest:
        inputs = prepare_execution_inputs(
            version=version,
            input_files=input_files,
            input_values=input_values,
            action_payload=action_payload,
        )
        workdir_archive = build_workdir_archive(
            version=version,
            input_files=inputs.normalized_input_files,
            memory_json=memory_json,
        )
        return RunnerRequest(
            env=inputs.env,
            normalized_input_files=inputs.normalized_input_files,
            input_manifest_json=inputs.input_manifest_json,
            inputs_json=inputs.inputs_json,
            request_json_bytes=None,
            workdir_archive=workdir_archive,
        )
