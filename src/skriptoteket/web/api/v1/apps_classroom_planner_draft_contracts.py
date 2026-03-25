"""Shared draft DTOs and serializers for classroom-planner API routes.

This module holds the draft-level response contract that multiple classroom
planner routers expose. Keeping the DTO and serializer here avoids router
modules depending on each other's private helpers while preserving one public
shape for the mutable planner draft root.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.curated_apps.classroom_planner.models import PlanDraft, PlanDraftKind


class PlanDraftDto(BaseModel):
    """Serialize the mutable draft root."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    roster_id: UUID
    draft_kind: PlanDraftKind
    template_id: UUID | None = None
    smart_enabled: bool = False
    status: str
    revision: int
    last_opened_at: datetime


def serialize_plan_draft(draft: PlanDraft) -> PlanDraftDto:
    """Map a draft aggregate to the public API response."""

    return PlanDraftDto.model_validate(draft)
