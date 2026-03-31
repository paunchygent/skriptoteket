"""Workspace-building helpers for classroom-planner draft handlers.

These helpers build and transform mutable draft workspaces without depending on
web or persistence concerns. Keeping them here prevents lifecycle handlers from
mixing pure workspace construction with transaction orchestration.
"""

from __future__ import annotations

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    DraftGroup,
    DraftWorkspace,
    PlanDraft,
    PlanDraftStatus,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.id_generator import IdGeneratorProtocol


def build_default_groups(
    *,
    id_generator: IdGeneratorProtocol,
    count: int = 6,
) -> list[DraftGroup]:
    """Create the default group buckets for a new grouping draft."""

    return [
        DraftGroup(
            id=f"group-{index}-{id_generator.new_uuid().hex[:8]}",
            name=f"Grupp {index}",
            sort_order=index - 1,
            name_is_custom=False,
        )
        for index in range(1, count + 1)
    ]


def build_initial_workspace(
    *,
    draft: PlanDraft,
    id_generator: IdGeneratorProtocol,
) -> DraftWorkspace:
    """Create the initial fundamentals workspace payload for a new draft."""

    return DraftWorkspace(
        draft=draft,
        groups=build_default_groups(id_generator=id_generator),
        group_assignments=[],
        seat_assignments=[],
    )


def build_recontextualized_workspace(
    *,
    workspace: DraftWorkspace,
    draft: PlanDraft,
) -> DraftWorkspace:
    """Keep one active draft while refreshing room-bound seating context."""

    return workspace.model_copy(
        update={
            "draft": draft,
            "seat_assignments": [],
        }
    )


def ensure_active_draft(*, draft: PlanDraft) -> None:
    """Reject mutations against drafts that are no longer active."""

    if draft.status == PlanDraftStatus.ACTIVE:
        return
    raise DomainError(
        code=ErrorCode.CONFLICT,
        message=(
            "Det här utkastet är inte längre aktivt. "
            "Gå tillbaka till startsidan och öppna planeringen igen."
        ),
        details={
            "draft_id": str(draft.id),
            "status": draft.status.value,
            "reason": "inactive_draft",
        },
    )
