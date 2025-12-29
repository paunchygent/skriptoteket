from __future__ import annotations

import hashlib
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.domain.scripting.tool_inputs import (
    ToolInputSchema,
    normalize_tool_input_schema,
)
from skriptoteket.domain.scripting.tool_settings import (
    ToolSettingsSchema,
    normalize_tool_settings_schema,
)
from skriptoteket.domain.scripting.ui.contract_v2 import UiActionField


class VersionState(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    ACTIVE = "active"
    ARCHIVED = "archived"


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
