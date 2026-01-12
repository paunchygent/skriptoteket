from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.domain.scripting.input_files import InputManifest
from skriptoteket.domain.scripting.ui.contract_v2 import UiPayloadV2


class RunContext(StrEnum):
    SANDBOX = "sandbox"
    PRODUCTION = "production"


class RunSourceKind(StrEnum):
    TOOL_VERSION = "tool_version"
    CURATED_APP = "curated_app"


class RunStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


class ToolRun(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    tool_id: UUID
    source_kind: RunSourceKind = RunSourceKind.TOOL_VERSION
    version_id: UUID | None = None
    snapshot_id: UUID | None = None
    curated_app_id: str | None = None
    curated_app_version: str | None = None
    context: RunContext
    requested_by_user_id: UUID
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None = None

    workdir_path: str
    input_filename: str | None = None
    input_size_bytes: int
    input_manifest: InputManifest
    input_values: dict[str, JsonValue] = Field(default_factory=dict)

    html_output: str | None = None
    stdout: str | None = None
    stderr: str | None = None
    artifacts_manifest: dict[str, object]
    error_summary: str | None = None
    ui_payload: UiPayloadV2 | None = None

    @model_validator(mode="after")
    def _validate_source_fields(self) -> "ToolRun":
        if self.source_kind is RunSourceKind.TOOL_VERSION:
            if self.version_id is None:
                raise ValueError("version_id is required for tool_version runs")
            if self.curated_app_id is not None or self.curated_app_version is not None:
                raise ValueError("curated app fields must be null for tool_version runs")
            return self

        if self.source_kind is RunSourceKind.CURATED_APP:
            if self.version_id is not None:
                raise ValueError("version_id must be null for curated_app runs")
            if self.curated_app_id is None or not self.curated_app_id.strip():
                raise ValueError("curated_app_id is required for curated_app runs")
            if self.curated_app_version is None or not self.curated_app_version.strip():
                raise ValueError("curated_app_version is required for curated_app runs")
            return self

        raise ValueError(f"Unknown RunSourceKind: {self.source_kind}")


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized if normalized else None


def start_tool_version_run(
    *,
    run_id: UUID,
    tool_id: UUID,
    version_id: UUID,
    snapshot_id: UUID | None = None,
    context: RunContext,
    requested_by_user_id: UUID,
    workdir_path: str,
    input_filename: str | None,
    input_size_bytes: int,
    input_manifest: InputManifest,
    input_values: dict[str, JsonValue] | None = None,
    now: datetime,
) -> ToolRun:
    normalized_workdir_path = workdir_path.strip()
    if not normalized_workdir_path:
        raise validation_error("workdir_path is required")
    normalized_input_filename: str | None = None
    if input_filename is not None:
        stripped = input_filename.strip()
        if not stripped:
            raise validation_error("input_filename must not be blank")
        normalized_input_filename = stripped
    if input_size_bytes < 0:
        raise validation_error(
            "input_size_bytes must be >= 0", details={"input_size_bytes": input_size_bytes}
        )

    normalized_input_values = input_values if input_values is not None else {}

    return ToolRun(
        id=run_id,
        tool_id=tool_id,
        source_kind=RunSourceKind.TOOL_VERSION,
        version_id=version_id,
        snapshot_id=snapshot_id,
        curated_app_id=None,
        curated_app_version=None,
        context=context,
        requested_by_user_id=requested_by_user_id,
        status=RunStatus.RUNNING,
        started_at=now,
        workdir_path=normalized_workdir_path,
        input_filename=normalized_input_filename,
        input_size_bytes=input_size_bytes,
        input_manifest=input_manifest,
        input_values=normalized_input_values,
        artifacts_manifest={},
    )


def start_curated_app_run(
    *,
    run_id: UUID,
    tool_id: UUID,
    curated_app_id: str,
    curated_app_version: str,
    context: RunContext,
    requested_by_user_id: UUID,
    workdir_path: str,
    input_filename: str | None,
    input_size_bytes: int,
    input_manifest: InputManifest,
    now: datetime,
) -> ToolRun:
    normalized_app_id = curated_app_id.strip()
    if not normalized_app_id:
        raise validation_error("curated_app_id is required")

    normalized_app_version = curated_app_version.strip()
    if not normalized_app_version:
        raise validation_error("curated_app_version is required")

    normalized_workdir_path = workdir_path.strip()
    if not normalized_workdir_path:
        raise validation_error("workdir_path is required")
    normalized_input_filename: str | None = None
    if input_filename is not None:
        stripped = input_filename.strip()
        if not stripped:
            raise validation_error("input_filename must not be blank")
        normalized_input_filename = stripped
    if input_size_bytes < 0:
        raise validation_error(
            "input_size_bytes must be >= 0", details={"input_size_bytes": input_size_bytes}
        )

    return ToolRun(
        id=run_id,
        tool_id=tool_id,
        source_kind=RunSourceKind.CURATED_APP,
        version_id=None,
        curated_app_id=normalized_app_id,
        curated_app_version=normalized_app_version,
        context=context,
        requested_by_user_id=requested_by_user_id,
        status=RunStatus.RUNNING,
        started_at=now,
        workdir_path=normalized_workdir_path,
        input_filename=normalized_input_filename,
        input_size_bytes=input_size_bytes,
        input_manifest=input_manifest,
        artifacts_manifest={"artifacts": []},
    )


def finish_run(
    *,
    run: ToolRun,
    status: RunStatus,
    now: datetime,
    stdout: str | None,
    stderr: str | None,
    artifacts_manifest: dict[str, object],
    error_summary: str | None,
    ui_payload: UiPayloadV2 | None,
) -> ToolRun:
    if run.status is not RunStatus.RUNNING:
        raise DomainError(
            code=ErrorCode.CONFLICT,
            message="Only running runs can be finished",
            details={"status": run.status.value},
        )
    if status is RunStatus.RUNNING:
        raise validation_error("finish_tool_run requires a terminal status")
    if now < run.started_at:
        raise validation_error(
            "finished_at cannot be before started_at",
            details={"started_at": run.started_at.isoformat(), "finished_at": now.isoformat()},
        )

    return run.model_copy(
        update={
            "status": status,
            "finished_at": now,
            "stdout": stdout,
            "stderr": stderr,
            "artifacts_manifest": artifacts_manifest,
            "error_summary": _normalize_optional_text(error_summary),
            "ui_payload": ui_payload,
        }
    )
