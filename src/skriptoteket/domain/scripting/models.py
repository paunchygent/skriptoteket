from __future__ import annotations

import hashlib
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.domain.scripting.input_files import InputManifest
from skriptoteket.domain.scripting.tool_inputs import (
    ToolInputSchema,
    normalize_tool_input_schema,
)
from skriptoteket.domain.scripting.tool_settings import (
    ToolSettingsSchema,
    normalize_tool_settings_schema,
)
from skriptoteket.domain.scripting.ui.contract_v2 import UiActionField, UiPayloadV2


class VersionState(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    ACTIVE = "active"
    ARCHIVED = "archived"


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


class ToolVersion(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    tool_id: UUID
    version_number: int
    state: VersionState

    source_code: str
    entrypoint: str
    content_hash: str
    settings_schema: list[UiActionField] | None = None
    input_schema: ToolInputSchema | None = None
    usage_instructions: str | None = None
    derived_from_version_id: UUID | None = None

    created_by_user_id: UUID
    created_at: datetime

    submitted_for_review_by_user_id: UUID | None = None
    submitted_for_review_at: datetime | None = None

    reviewed_by_user_id: UUID | None = None
    reviewed_at: datetime | None = None

    published_by_user_id: UUID | None = None
    published_at: datetime | None = None

    change_summary: str | None = None
    review_note: str | None = None


class ToolRun(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    tool_id: UUID
    source_kind: RunSourceKind = RunSourceKind.TOOL_VERSION
    version_id: UUID | None = None
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
    def _validate_source_fields(self) -> ToolRun:
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


class PublishVersionResult(BaseModel):
    """Result of a copy-on-activate publish action."""

    model_config = ConfigDict(frozen=True)

    new_active_version: ToolVersion
    archived_reviewed_version: ToolVersion
    archived_previous_active_version: ToolVersion | None = None


class RollbackVersionResult(BaseModel):
    """Result of a rollback action."""

    model_config = ConfigDict(frozen=True)

    new_active_version: ToolVersion
    archived_previous_active_version: ToolVersion | None = None


def compute_content_hash(*, entrypoint: str, source_code: str) -> str:
    content = f"{entrypoint}\n{source_code}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _validate_version_number(*, version_number: int) -> None:
    if version_number < 1:
        raise validation_error(
            "version_number must be >= 1", details={"version_number": version_number}
        )


def _validate_entrypoint(*, entrypoint: str) -> str:
    normalized_entrypoint = entrypoint.strip()
    if not normalized_entrypoint:
        raise validation_error("entrypoint is required")
    if len(normalized_entrypoint) > 128:
        raise validation_error("entrypoint must be 128 characters or less")
    return normalized_entrypoint


def _validate_source_code(*, source_code: str) -> str:
    if not source_code:
        raise validation_error("source_code is required")
    return source_code


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized if normalized else None


def create_draft_version(
    *,
    version_id: UUID,
    tool_id: UUID,
    version_number: int,
    source_code: str,
    entrypoint: str,
    settings_schema: ToolSettingsSchema | None = None,
    input_schema: ToolInputSchema | None = None,
    usage_instructions: str | None = None,
    created_by_user_id: UUID,
    derived_from_version_id: UUID | None,
    change_summary: str | None,
    now: datetime,
) -> ToolVersion:
    _validate_version_number(version_number=version_number)
    normalized_entrypoint = _validate_entrypoint(entrypoint=entrypoint)
    normalized_source_code = _validate_source_code(source_code=source_code)

    return ToolVersion(
        id=version_id,
        tool_id=tool_id,
        version_number=version_number,
        state=VersionState.DRAFT,
        source_code=normalized_source_code,
        entrypoint=normalized_entrypoint,
        content_hash=compute_content_hash(
            entrypoint=normalized_entrypoint,
            source_code=normalized_source_code,
        ),
        settings_schema=normalize_tool_settings_schema(settings_schema=settings_schema),
        input_schema=normalize_tool_input_schema(input_schema=input_schema),
        usage_instructions=_normalize_optional_text(usage_instructions),
        derived_from_version_id=derived_from_version_id,
        created_by_user_id=created_by_user_id,
        created_at=now,
        change_summary=_normalize_optional_text(change_summary),
    )


def save_draft_snapshot(
    *,
    previous_version: ToolVersion,
    new_version_id: UUID,
    new_version_number: int,
    source_code: str,
    entrypoint: str,
    settings_schema: ToolSettingsSchema | None = None,
    input_schema: ToolInputSchema | None = None,
    usage_instructions: str | None = None,
    saved_by_user_id: UUID,
    change_summary: str | None,
    now: datetime,
) -> ToolVersion:
    if previous_version.state is not VersionState.DRAFT:
        raise DomainError(
            code=ErrorCode.CONFLICT,
            message="Only draft versions can be saved",
            details={"state": previous_version.state.value},
        )
    if new_version_number <= previous_version.version_number:
        raise validation_error(
            "new_version_number must be greater than previous version_number",
            details={
                "previous_version_number": previous_version.version_number,
                "new_version_number": new_version_number,
            },
        )

    _validate_version_number(version_number=new_version_number)
    normalized_entrypoint = _validate_entrypoint(entrypoint=entrypoint)
    normalized_source_code = _validate_source_code(source_code=source_code)

    return ToolVersion(
        id=new_version_id,
        tool_id=previous_version.tool_id,
        version_number=new_version_number,
        state=VersionState.DRAFT,
        source_code=normalized_source_code,
        entrypoint=normalized_entrypoint,
        content_hash=compute_content_hash(
            entrypoint=normalized_entrypoint,
            source_code=normalized_source_code,
        ),
        settings_schema=normalize_tool_settings_schema(settings_schema=settings_schema),
        input_schema=normalize_tool_input_schema(input_schema=input_schema),
        usage_instructions=_normalize_optional_text(usage_instructions),
        derived_from_version_id=previous_version.id,
        created_by_user_id=saved_by_user_id,
        created_at=now,
        change_summary=_normalize_optional_text(change_summary),
    )


def submit_for_review(
    *,
    version: ToolVersion,
    submitted_by_user_id: UUID,
    review_note: str | None,
    now: datetime,
) -> ToolVersion:
    if version.state is not VersionState.DRAFT:
        raise DomainError(
            code=ErrorCode.CONFLICT,
            message="Only draft versions can be submitted for review",
            details={"state": version.state.value},
        )

    return version.model_copy(
        update={
            "state": VersionState.IN_REVIEW,
            "submitted_for_review_by_user_id": submitted_by_user_id,
            "submitted_for_review_at": now,
            "review_note": _normalize_optional_text(review_note),
        }
    )


def publish_version(
    *,
    reviewed_version: ToolVersion,
    new_active_version_id: UUID,
    new_active_version_number: int,
    published_by_user_id: UUID,
    now: datetime,
    change_summary: str | None,
    previous_active_version: ToolVersion | None,
) -> PublishVersionResult:
    if reviewed_version.state is not VersionState.IN_REVIEW:
        raise DomainError(
            code=ErrorCode.CONFLICT,
            message="Only in_review versions can be published",
            details={"state": reviewed_version.state.value},
        )
    if previous_active_version is not None:
        if previous_active_version.tool_id != reviewed_version.tool_id:
            raise validation_error(
                "previous_active_version must belong to the same tool",
                details={
                    "previous_active_tool_id": str(previous_active_version.tool_id),
                    "tool_id": str(reviewed_version.tool_id),
                },
            )
        if previous_active_version.state is not VersionState.ACTIVE:
            raise validation_error(
                "previous_active_version must be active",
                details={"state": previous_active_version.state.value},
            )

    _validate_version_number(version_number=new_active_version_number)

    archived_previous = (
        previous_active_version.model_copy(update={"state": VersionState.ARCHIVED})
        if previous_active_version is not None
        else None
    )

    archived_reviewed = reviewed_version.model_copy(
        update={
            "state": VersionState.ARCHIVED,
            "published_by_user_id": published_by_user_id,
            "published_at": now,
        }
    )

    active_change_summary = (
        _normalize_optional_text(change_summary)
        if change_summary is not None
        else archived_reviewed.change_summary
    )

    new_active = ToolVersion(
        id=new_active_version_id,
        tool_id=reviewed_version.tool_id,
        version_number=new_active_version_number,
        state=VersionState.ACTIVE,
        source_code=reviewed_version.source_code,
        entrypoint=reviewed_version.entrypoint,
        content_hash=reviewed_version.content_hash,
        settings_schema=reviewed_version.settings_schema,
        input_schema=reviewed_version.input_schema,
        usage_instructions=reviewed_version.usage_instructions,
        derived_from_version_id=reviewed_version.id,
        created_by_user_id=published_by_user_id,
        created_at=now,
        published_by_user_id=published_by_user_id,
        published_at=now,
        change_summary=active_change_summary,
    )

    return PublishVersionResult(
        new_active_version=new_active,
        archived_reviewed_version=archived_reviewed,
        archived_previous_active_version=archived_previous,
    )


def rollback_to_version(
    *,
    archived_version: ToolVersion,
    new_active_version_id: UUID,
    new_active_version_number: int,
    published_by_user_id: UUID,
    now: datetime,
    previous_active_version: ToolVersion | None,
) -> RollbackVersionResult:
    if archived_version.state is not VersionState.ARCHIVED:
        raise DomainError(
            code=ErrorCode.CONFLICT,
            message="Only archived versions can be rolled back to",
            details={"state": archived_version.state.value},
        )
    if previous_active_version is not None:
        if previous_active_version.tool_id != archived_version.tool_id:
            raise validation_error(
                "previous_active_version must belong to the same tool",
                details={
                    "previous_active_tool_id": str(previous_active_version.tool_id),
                    "tool_id": str(archived_version.tool_id),
                },
            )
        if previous_active_version.state is not VersionState.ACTIVE:
            raise validation_error(
                "previous_active_version must be active",
                details={"state": previous_active_version.state.value},
            )

    _validate_version_number(version_number=new_active_version_number)

    archived_previous = (
        previous_active_version.model_copy(update={"state": VersionState.ARCHIVED})
        if previous_active_version is not None
        else None
    )

    new_active = ToolVersion(
        id=new_active_version_id,
        tool_id=archived_version.tool_id,
        version_number=new_active_version_number,
        state=VersionState.ACTIVE,
        source_code=archived_version.source_code,
        entrypoint=archived_version.entrypoint,
        content_hash=archived_version.content_hash,
        settings_schema=archived_version.settings_schema,
        input_schema=archived_version.input_schema,
        usage_instructions=archived_version.usage_instructions,
        derived_from_version_id=archived_version.id,
        created_by_user_id=published_by_user_id,
        created_at=now,
        published_by_user_id=published_by_user_id,
        published_at=now,
        change_summary=f"Rollback from v{archived_version.version_number}",
    )

    return RollbackVersionResult(
        new_active_version=new_active,
        archived_previous_active_version=archived_previous,
    )


def start_tool_version_run(
    *,
    run_id: UUID,
    tool_id: UUID,
    version_id: UUID,
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
    input_filename: str,
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
    normalized_input_filename = input_filename.strip()
    if not normalized_input_filename:
        raise validation_error("input_filename is required")
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
