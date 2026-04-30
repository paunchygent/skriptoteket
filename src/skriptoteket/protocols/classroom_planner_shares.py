"""Protocols for Klassrumskartan share artifact persistence.

Purpose:
    Keep share-link application handlers behind repository protocols so
    persistence stays replaceable and transaction ownership remains in the
    application Unit of Work.

Relationships:
    - Implemented by `infrastructure.repositories.classroom_planner_share_artifacts`.
    - Consumed by classroom-planner share handlers and future public read routes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    PreparedGroupingExportContract,
    PreparedSeatingExportContract,
)
from skriptoteket.application.curated_apps.classroom_planner.shares import (
    ClassroomPlannerShareArtifact,
    RenderedClassroomPlannerShare,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import PlanDraftKind


class ClassroomPlannerShareArtifactRepositoryProtocol(Protocol):
    """Persist and query immutable classroom-planner share artifacts."""

    async def create(
        self,
        *,
        artifact: ClassroomPlannerShareArtifact,
    ) -> ClassroomPlannerShareArtifact: ...

    async def get_by_id(
        self,
        *,
        share_id: UUID,
    ) -> ClassroomPlannerShareArtifact | None: ...

    async def get_by_token_hash(
        self,
        *,
        token_hash: str,
    ) -> ClassroomPlannerShareArtifact | None: ...

    async def list_for_owner_draft(
        self,
        *,
        owner_user_id: UUID,
        draft_id: UUID,
        draft_kind: PlanDraftKind,
    ) -> list[ClassroomPlannerShareArtifact]: ...

    async def revoke_owned(
        self,
        *,
        share_id: UUID,
        owner_user_id: UUID,
        revoked_at: datetime,
    ) -> ClassroomPlannerShareArtifact | None: ...

    async def revoke_for_draft_lifecycle(
        self,
        *,
        owner_user_id: UUID,
        draft_id: UUID,
        draft_kind: PlanDraftKind,
        revoked_at: datetime,
    ) -> int: ...

    async def revoke_for_roster_lifecycle(
        self,
        *,
        owner_user_id: UUID,
        roster_id: UUID,
        revoked_at: datetime,
    ) -> int: ...

    async def revoke_for_template_lifecycle(
        self,
        *,
        owner_user_id: UUID,
        template_id: UUID,
        revoked_at: datetime,
    ) -> int: ...

    async def revoke_for_owner_lifecycle(
        self,
        *,
        owner_user_id: UUID,
        revoked_at: datetime,
        detach_owner: bool,
    ) -> int: ...


class ClassroomPlannerShareOwnerLifecycleProtocol(Protocol):
    """Apply account lifecycle changes to owned share artifacts."""

    async def revoke_for_owner_delete(
        self,
        *,
        owner_user_id: UUID,
    ) -> int: ...


class ClassroomPlannerShareRendererProtocol(Protocol):
    """Render immutable classroom-planner share pages from canonical presentations."""

    def render_grouping(
        self,
        *,
        prepared_export: PreparedGroupingExportContract,
    ) -> RenderedClassroomPlannerShare: ...

    def render_seating(
        self,
        *,
        prepared_export: PreparedSeatingExportContract,
    ) -> RenderedClassroomPlannerShare: ...
