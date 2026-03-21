"""Planning handlers for validation, suggestions, randomization, and snapshots.

This module owns the higher-level classroom planner use cases that operate on a
hydrated workspace: validation, suggestion generation, suggestion application,
randomized assignment, and transactional finalization into immutable snapshots.
"""

from __future__ import annotations

import random
from uuid import UUID

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ArrangementSnapshot,
    ClassroomPlannerWorkspace,
    DraftWorkspace,
    PlanDraft,
    SuggestionList,
    ValidationResult,
)
from skriptoteket.domain.curated_apps.classroom_planner.suggestions import (
    build_profile_suggestions,
    build_randomized_suggestion,
    build_suggestion_by_id,
)
from skriptoteket.domain.curated_apps.classroom_planner.validation import validate_workspace
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found, validation_error
from skriptoteket.protocols.classroom_planner import (
    ArrangementSnapshotRepositoryProtocol,
    PlanDraftRepositoryProtocol,
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


async def _load_workspace_context(
    *,
    draft_id: UUID,
    owner_user_id: UUID,
    drafts: PlanDraftRepositoryProtocol,
    rosters: RosterRepositoryProtocol,
    templates: RoomTemplateRepositoryProtocol,
) -> tuple[DraftWorkspace, ClassroomPlannerWorkspace]:
    workspace = await drafts.get_workspace(draft_id=draft_id)
    if not workspace or workspace.draft.owner_user_id != owner_user_id:
        raise not_found("PlanDraft", str(draft_id))
    roster = await rosters.get_by_id(roster_id=workspace.draft.roster_id)
    if not roster or roster.owner_user_id != owner_user_id:
        raise not_found("Roster", str(workspace.draft.roster_id))
    template = await templates.get_by_id(template_id=workspace.draft.template_id)
    if not template or template.owner_user_id != owner_user_id:
        raise not_found("RoomTemplate", str(workspace.draft.template_id))
    return workspace, ClassroomPlannerWorkspace(
        draft=workspace.draft,
        roster=roster,
        template=template,
        groups=workspace.groups,
        group_assignments=workspace.group_assignments,
        seat_assignments=workspace.seat_assignments,
        student_planning_meta=workspace.student_planning_meta,
        pair_constraints=workspace.pair_constraints,
        planning_profile=workspace.planning_profile,
    )


class ValidateDraftHandler:
    """Run authoritative validation over the current workspace."""

    def __init__(
        self,
        drafts: PlanDraftRepositoryProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
    ) -> None:
        self._drafts = drafts
        self._rosters = rosters
        self._templates = templates

    async def handle(self, *, draft_id: UUID, owner_user_id: UUID) -> ValidationResult:
        _, workspace = await _load_workspace_context(
            draft_id=draft_id,
            owner_user_id=owner_user_id,
            drafts=self._drafts,
            rosters=self._rosters,
            templates=self._templates,
        )
        return validate_workspace(workspace=workspace)


class GenerateSuggestionsHandler:
    """Build explainable profile-based suggestions for the planner."""

    def __init__(
        self,
        drafts: PlanDraftRepositoryProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._drafts = drafts
        self._rosters = rosters
        self._templates = templates
        self._clock = clock

    async def handle(self, *, draft_id: UUID, owner_user_id: UUID) -> SuggestionList:
        _, workspace = await _load_workspace_context(
            draft_id=draft_id,
            owner_user_id=owner_user_id,
            drafts=self._drafts,
            rosters=self._rosters,
            templates=self._templates,
        )
        return build_profile_suggestions(workspace=workspace, generated_at=self._clock.now())


class ApplySuggestionHandler:
    """Apply a generated profile suggestion to the mutable draft."""

    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._drafts = drafts
        self._rosters = rosters
        self._templates = templates
        self._clock = clock

    async def handle(
        self,
        *,
        draft_id: UUID,
        owner_user_id: UUID,
        suggestion_id: str,
        expected_revision: int | None = None,
    ) -> PlanDraft:
        workspace, hydrated = await _load_workspace_context(
            draft_id=draft_id,
            owner_user_id=owner_user_id,
            drafts=self._drafts,
            rosters=self._rosters,
            templates=self._templates,
        )
        if expected_revision is not None and workspace.draft.revision != expected_revision:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message=(
                    "Draft revision mismatch. "
                    f"Expected {expected_revision}, got {workspace.draft.revision}."
                ),
            )
        try:
            suggestion = build_suggestion_by_id(
                workspace=hydrated,
                suggestion_id=suggestion_id,
                generated_at=self._clock.now(),
            )
        except KeyError as exc:
            raise validation_error(f"Unknown suggestion id: {suggestion_id}") from exc
        updated_workspace = workspace.model_copy(
            update={
                "draft": workspace.draft.model_copy(
                    update={
                        "revision": workspace.draft.revision + 1,
                        "updated_at": self._clock.now(),
                        "engine_metadata": suggestion.engine_metadata,
                    }
                ),
                "groups": suggestion.groups,
                "group_assignments": suggestion.group_assignments,
                "seat_assignments": suggestion.seat_assignments,
            }
        )
        async with self._uow:
            await self._drafts.save_workspace(workspace=updated_workspace)
        return updated_workspace.draft


class RandomizeDraftHandler:
    """Randomly assign all students to groups and seats for the Slumpa action."""

    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._drafts = drafts
        self._rosters = rosters
        self._templates = templates
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        draft_id: UUID,
        owner_user_id: UUID,
        expected_revision: int | None = None,
    ) -> PlanDraft:
        workspace, hydrated = await _load_workspace_context(
            draft_id=draft_id,
            owner_user_id=owner_user_id,
            drafts=self._drafts,
            rosters=self._rosters,
            templates=self._templates,
        )
        if expected_revision is not None and workspace.draft.revision != expected_revision:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message=(
                    "Draft revision mismatch. "
                    f"Expected {expected_revision}, got {workspace.draft.revision}."
                ),
            )
        rng = random.Random(self._id_generator.new_uuid().int)
        suggestion = build_randomized_suggestion(
            workspace=hydrated,
            generated_at=self._clock.now(),
            rng=rng,
        )
        updated_workspace = workspace.model_copy(
            update={
                "draft": workspace.draft.model_copy(
                    update={
                        "revision": workspace.draft.revision + 1,
                        "updated_at": self._clock.now(),
                        "engine_metadata": suggestion.engine_metadata,
                    }
                ),
                "groups": suggestion.groups,
                "group_assignments": suggestion.group_assignments,
                "seat_assignments": suggestion.seat_assignments,
            }
        )
        async with self._uow:
            await self._drafts.save_workspace(workspace=updated_workspace)
        return updated_workspace.draft


class FinalizeDraftHandler:
    """Create an immutable arrangement snapshot from the current workspace."""

    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
        snapshots: ArrangementSnapshotRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._drafts = drafts
        self._rosters = rosters
        self._templates = templates
        self._snapshots = snapshots
        self._clock = clock
        self._id_generator = id_generator

    async def handle(self, *, draft_id: UUID, owner_user_id: UUID) -> ArrangementSnapshot:
        _, workspace = await _load_workspace_context(
            draft_id=draft_id,
            owner_user_id=owner_user_id,
            drafts=self._drafts,
            rosters=self._rosters,
            templates=self._templates,
        )
        validation = validate_workspace(workspace=workspace)
        hard_findings = [
            finding.model_dump(mode="json")
            for finding in validation.findings
            if finding.severity.value == "hard"
        ]
        if hard_findings:
            raise validation_error(
                "Draft has blocking validation findings and cannot be finalized.",
                details={"findings": hard_findings},
            )

        snapshot = ArrangementSnapshot(
            id=self._id_generator.new_uuid(),
            owner_user_id=owner_user_id,
            source_draft_id=workspace.draft.id,
            lesson_mode_id=workspace.draft.lesson_mode_id,
            snapshot_schema_version=1,
            payload={
                "roster": workspace.roster.model_dump(mode="json"),
                "template": workspace.template.model_dump(mode="json"),
                "groups": [group.model_dump(mode="json") for group in workspace.groups],
                "group_assignments": [
                    assignment.model_dump(mode="json") for assignment in workspace.group_assignments
                ],
                "seat_assignments": [
                    assignment.model_dump(mode="json") for assignment in workspace.seat_assignments
                ],
                "student_planning_meta": [
                    meta.model_dump(mode="json") for meta in workspace.student_planning_meta
                ],
                "pair_constraints": [
                    constraint.model_dump(mode="json") for constraint in workspace.pair_constraints
                ],
                "planning_profile": workspace.planning_profile.model_dump(mode="json"),
                "engine_metadata": (
                    workspace.draft.engine_metadata.model_dump(mode="json")
                    if workspace.draft.engine_metadata
                    else None
                ),
                "validation_findings": [
                    finding.model_dump(mode="json") for finding in validation.findings
                ],
            },
            created_at=self._clock.now(),
        )
        async with self._uow:
            await self._snapshots.save(snapshot=snapshot)
        return snapshot


class ListSnapshotsHandler:
    """List immutable arrangement snapshots for the current user."""

    def __init__(self, snapshots: ArrangementSnapshotRepositoryProtocol) -> None:
        self._snapshots = snapshots

    async def handle(self, *, owner_user_id: UUID) -> list[ArrangementSnapshot]:
        return await self._snapshots.list_by_owner(owner_user_id=owner_user_id)


class GetSnapshotHandler:
    """Load one immutable arrangement snapshot for the current user."""

    def __init__(self, snapshots: ArrangementSnapshotRepositoryProtocol) -> None:
        self._snapshots = snapshots

    async def handle(self, *, snapshot_id: UUID, owner_user_id: UUID) -> ArrangementSnapshot:
        snapshot = await self._snapshots.get_by_id(snapshot_id=snapshot_id)
        if not snapshot or snapshot.owner_user_id != owner_user_id:
            raise not_found("ArrangementSnapshot", str(snapshot_id))
        return snapshot
