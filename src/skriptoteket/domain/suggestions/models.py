from __future__ import annotations

from collections.abc import Collection
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error


class SuggestionStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    ACCEPTED = "accepted"
    DENIED = "denied"


class SuggestionDecisionType(StrEnum):
    ACCEPT = "accept"
    DENY = "deny"


class SuggestionDecision(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    suggestion_id: UUID
    decided_by_user_id: UUID
    decision: SuggestionDecisionType
    rationale: str

    title: str
    description: str
    profession_slugs: tuple[str, ...]
    category_slugs: tuple[str, ...]

    created_tool_id: UUID | None = None
    decided_at: datetime


class Suggestion(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    submitted_by_user_id: UUID

    title: str
    description: str

    profession_slugs: tuple[str, ...]
    category_slugs: tuple[str, ...]

    status: SuggestionStatus
    reviewed_by_user_id: UUID | None = None
    reviewed_at: datetime | None = None
    review_rationale: str | None = None
    draft_tool_id: UUID | None = None

    created_at: datetime
    updated_at: datetime


def _validate_title(*, title: str) -> str:
    normalized_title = title.strip()
    if not normalized_title:
        raise validation_error("Title is required")
    if len(normalized_title) > 255:
        raise validation_error("Title must be 255 characters or less")
    return normalized_title


def _validate_description(*, description: str) -> str:
    normalized_description = description.strip()
    if not normalized_description:
        raise validation_error("Description is required")
    return normalized_description


def _validate_profession_slugs(*, profession_slugs: Collection[str]) -> tuple[str, ...]:
    professions = tuple(slug.strip() for slug in profession_slugs)
    if not professions:
        raise validation_error("At least one profession is required")
    if len(set(professions)) != len(professions):
        raise validation_error("Duplicate professions are not allowed")
    if any(not slug for slug in professions):
        raise validation_error("Profession slugs must not be empty")
    return professions


def _validate_category_slugs(*, category_slugs: Collection[str]) -> tuple[str, ...]:
    categories = tuple(slug.strip() for slug in category_slugs)
    if not categories:
        raise validation_error("At least one category is required")
    if len(set(categories)) != len(categories):
        raise validation_error("Duplicate categories are not allowed")
    if any(not slug for slug in categories):
        raise validation_error("Category slugs must not be empty")
    return categories


def create_suggestion(
    *,
    suggestion_id: UUID,
    submitted_by_user_id: UUID,
    title: str,
    description: str,
    profession_slugs: Collection[str],
    category_slugs: Collection[str],
    now: datetime,
) -> Suggestion:
    normalized_title = _validate_title(title=title)
    normalized_description = _validate_description(description=description)

    professions = _validate_profession_slugs(profession_slugs=profession_slugs)
    categories = _validate_category_slugs(category_slugs=category_slugs)

    return Suggestion(
        id=suggestion_id,
        submitted_by_user_id=submitted_by_user_id,
        title=normalized_title,
        description=normalized_description,
        profession_slugs=professions,
        category_slugs=categories,
        status=SuggestionStatus.PENDING_REVIEW,
        created_at=now,
        updated_at=now,
    )


def decide_suggestion(
    *,
    suggestion: Suggestion,
    decision_id: UUID,
    decided_by_user_id: UUID,
    decision: SuggestionDecisionType,
    rationale: str,
    title: str | None,
    description: str | None,
    profession_slugs: Collection[str] | None,
    category_slugs: Collection[str] | None,
    created_tool_id: UUID | None,
    now: datetime,
) -> tuple[Suggestion, SuggestionDecision]:
    if suggestion.status is not SuggestionStatus.PENDING_REVIEW:
        raise DomainError(
            code=ErrorCode.CONFLICT,
            message="Suggestion has already been reviewed",
            details={"status": suggestion.status},
        )

    normalized_rationale = rationale.strip()
    if not normalized_rationale:
        raise validation_error("Rationale is required")

    final_title = _validate_title(title=(title if title is not None else suggestion.title))
    final_description = _validate_description(
        description=(description if description is not None else suggestion.description)
    )
    final_professions = _validate_profession_slugs(
        profession_slugs=(
            profession_slugs if profession_slugs is not None else suggestion.profession_slugs
        )
    )
    final_categories = _validate_category_slugs(
        category_slugs=(category_slugs if category_slugs is not None else suggestion.category_slugs)
    )

    if decision is SuggestionDecisionType.ACCEPT and created_tool_id is None:
        raise validation_error("Accepted suggestions must create a draft tool")
    if decision is SuggestionDecisionType.DENY and created_tool_id is not None:
        raise validation_error("Denied suggestions must not create a tool")

    new_status = (
        SuggestionStatus.ACCEPTED
        if decision is SuggestionDecisionType.ACCEPT
        else SuggestionStatus.DENIED
    )
    updated_suggestion = suggestion.model_copy(
        update={
            "status": new_status,
            "reviewed_by_user_id": decided_by_user_id,
            "reviewed_at": now,
            "review_rationale": normalized_rationale,
            "draft_tool_id": created_tool_id,
            "updated_at": now,
        }
    )
    decision_record = SuggestionDecision(
        id=decision_id,
        suggestion_id=suggestion.id,
        decided_by_user_id=decided_by_user_id,
        decision=decision,
        rationale=normalized_rationale,
        title=final_title,
        description=final_description,
        profession_slugs=final_professions,
        category_slugs=final_categories,
        created_tool_id=created_tool_id,
        decided_at=now,
    )
    return updated_suggestion, decision_record
