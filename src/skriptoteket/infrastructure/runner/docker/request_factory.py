from dataclasses import dataclass
from typing import Protocol

from pydantic import JsonValue, ValidationError

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.models import ToolVersion
from skriptoteket.domain.scripting.run_inputs import ResolvedInputFile
from skriptoteket.infrastructure.runner.contracts.request_envelope_v1 import (
    RunnerRequestAction,
    RunnerRequestEnvelopeV1,
    RunnerRequestFile,
    RunnerRequestInputs,
    render_request_envelope_json,
)

from .env import prepare_execution_env
from .workdir_archive import WorkdirArchiveEntry, build_workdir_archive_from_entries


@dataclass(frozen=True, slots=True)
class RunnerRequest:
    env: dict[str, str]
    input_files: list[ResolvedInputFile]
    request_json_bytes: bytes
    workdir_archive: bytes


class RunnerRequestFactoryProtocol(Protocol):
    def build_request(
        self,
        *,
        version: ToolVersion,
        input_files: list[ResolvedInputFile],
        input_values: dict[str, JsonValue],
        memory_json: bytes,
        action_payload: dict[str, JsonValue] | None,
    ) -> RunnerRequest: ...


class V3RunnerRequestFactory:
    def build_request(
        self,
        *,
        version: ToolVersion,
        input_files: list[ResolvedInputFile],
        input_values: dict[str, JsonValue],
        memory_json: bytes,
        action_payload: dict[str, JsonValue] | None,
    ) -> RunnerRequest:
        env = prepare_execution_env(version=version)
        request_files = [
            RunnerRequestFile(
                name=entry.name,
                path=f"/work/input/{entry.name}",
                bytes=len(entry.content),
                ref=entry.ref,
                field=entry.field,
            )
            for entry in input_files
        ]
        action = _build_action_payload(action_payload=action_payload)
        envelope = RunnerRequestEnvelopeV1(
            inputs=RunnerRequestInputs(values=input_values),
            action=action,
            files=request_files,
        )
        request_json_bytes = render_request_envelope_json(payload=envelope)
        workdir_archive = _build_workdir_archive(
            version=version,
            input_files=input_files,
            memory_json=memory_json,
            request_json_bytes=request_json_bytes,
        )
        return RunnerRequest(
            env=env,
            input_files=input_files,
            request_json_bytes=request_json_bytes,
            workdir_archive=workdir_archive,
        )


def _build_action_payload(
    *,
    action_payload: dict[str, JsonValue] | None,
) -> RunnerRequestAction | None:
    if action_payload is None:
        return None
    try:
        return RunnerRequestAction.model_validate(action_payload)
    except ValidationError as exc:
        raise DomainError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Runner action payload validation failed.",
            details={"errors": exc.errors()},
        ) from exc


def _build_workdir_archive(
    *,
    version: ToolVersion,
    input_files: list[ResolvedInputFile],
    memory_json: bytes,
    request_json_bytes: bytes,
) -> bytes:
    script_bytes = version.source_code.encode("utf-8")
    entries: list[WorkdirArchiveEntry] = [
        WorkdirArchiveEntry.file(name="script.py", content=script_bytes),
        WorkdirArchiveEntry.file(name="memory.json", content=memory_json),
        WorkdirArchiveEntry.file(name="request.json", content=request_json_bytes),
        WorkdirArchiveEntry.directory(name="input"),
    ]
    for entry in input_files:
        entries.append(
            WorkdirArchiveEntry.file(
                name=f"input/{entry.name}",
                content=entry.content,
            )
        )
    return build_workdir_archive_from_entries(entries=entries)
