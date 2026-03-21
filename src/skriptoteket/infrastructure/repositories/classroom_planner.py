"""PostgreSQL repositories for classroom planner aggregates.

This module maps SQLAlchemy models to the typed classroom planner domain models.
It persists reusable teacher assets, mutable draft workspaces, and immutable
arrangement snapshots without leaking ORM details into the application layer.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ArrangementSnapshot,
    DraftGroup,
    DraftWorkspace,
    GroupAssignment,
    PairConstraint,
    PairConstraintKind,
    PlanDraft,
    PlanningProfile,
    PlanningProfileKind,
    RoomFixture,
    RoomFixtureType,
    RoomTemplate,
    Roster,
    Seat,
    SeatAssignment,
    Student,
    StudentPlanningMeta,
    SuggestionEngineMetadata,
    default_planning_profile,
)
from skriptoteket.infrastructure.db.models.classroom_planner_plan_draft import (
    ArrangementSnapshotModel,
    DraftGroupModel,
    GroupAssignmentModel,
    PairConstraintModel,
    PlanDraftModel,
    PlanningProfileModel,
    SeatAssignmentModel,
    StudentPlanningMetaModel,
)
from skriptoteket.infrastructure.db.models.classroom_planner_room_template import (
    RoomTemplateModel,
)
from skriptoteket.infrastructure.db.models.classroom_planner_roster import RosterModel
from skriptoteket.protocols.classroom_planner import (
    ArrangementSnapshotRepositoryProtocol,
    PlanDraftRepositoryProtocol,
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
)


class PostgreSQLPlanDraftRepository(PlanDraftRepositoryProtocol):
    """Persist draft roots and draft-scoped workspace state in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _replace_related_collection(
        self,
        *,
        model: PlanDraftModel,
        attribute_name: str,
        new_items: list[object],
    ) -> None:
        """Replace child rows without tripping natural-key uniqueness constraints."""
        existing_items = list(getattr(model, attribute_name))
        if existing_items:
            getattr(model, attribute_name).clear()
            await self._session.flush()
        getattr(model, attribute_name).extend(new_items)

    def _upsert_planning_profile(
        self,
        *,
        model: PlanDraftModel,
        profile: PlanningProfile,
    ) -> None:
        """Update the single draft planning profile in place when present."""
        if model.planning_profile is None:
            model.planning_profile = PlanningProfileModel()
        model.planning_profile.profile_kind = profile.profile_kind.value
        model.planning_profile.enable_student_meta = profile.enable_student_meta
        model.planning_profile.enable_pair_constraints = profile.enable_pair_constraints
        model.planning_profile.enable_zone_preferences = profile.enable_zone_preferences
        model.planning_profile.enable_history_rules = profile.enable_history_rules
        model.planning_profile.teacher_proximity_weight = profile.teacher_proximity_weight
        model.planning_profile.focus_support_weight = profile.focus_support_weight
        model.planning_profile.stability_weight = profile.stability_weight
        model.planning_profile.balance_weight = profile.balance_weight
        model.planning_profile.rotation_weight = profile.rotation_weight

    def _to_draft(self, model: PlanDraftModel) -> PlanDraft:
        engine_metadata = (
            SuggestionEngineMetadata.model_validate(model.engine_metadata)
            if model.engine_metadata
            else None
        )
        return PlanDraft(
            id=model.id,
            owner_user_id=model.owner_user_id,
            roster_id=model.roster_id,
            template_id=model.template_id,
            lesson_mode_id=model.lesson_mode_id,
            revision=model.revision,
            engine_metadata=engine_metadata,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_workspace(self, model: PlanDraftModel) -> DraftWorkspace:
        planning_profile = (
            PlanningProfile(
                profile_kind=PlanningProfileKind(model.planning_profile.profile_kind),
                enable_student_meta=model.planning_profile.enable_student_meta,
                enable_pair_constraints=model.planning_profile.enable_pair_constraints,
                enable_zone_preferences=model.planning_profile.enable_zone_preferences,
                enable_history_rules=model.planning_profile.enable_history_rules,
                teacher_proximity_weight=model.planning_profile.teacher_proximity_weight,
                focus_support_weight=model.planning_profile.focus_support_weight,
                stability_weight=model.planning_profile.stability_weight,
                balance_weight=model.planning_profile.balance_weight,
                rotation_weight=model.planning_profile.rotation_weight,
            )
            if model.planning_profile
            else default_planning_profile()
        )
        return DraftWorkspace(
            draft=self._to_draft(model),
            groups=[
                DraftGroup(id=group.group_id, name=group.name, sort_order=group.sort_order)
                for group in model.groups
            ],
            group_assignments=[
                GroupAssignment(student_id=assignment.student_id, group_id=assignment.group_id)
                for assignment in model.group_assignments
            ],
            seat_assignments=[
                SeatAssignment(student_id=assignment.student_id, seat_id=assignment.seat_id)
                for assignment in model.seat_assignments
            ],
            student_planning_meta=[
                StudentPlanningMeta(
                    student_id=meta.student_id,
                    teacher_proximity=meta.teacher_proximity,
                    independent_focus_support=meta.independent_focus_support,
                    stability_preference=meta.stability_preference,
                    preferred_zone=meta.preferred_zone,
                    avoid_zone=meta.avoid_zone,
                    notes=meta.notes,
                )
                for meta in model.student_planning_meta
            ],
            pair_constraints=[
                PairConstraint(
                    student_id_a=constraint.student_id_a,
                    student_id_b=constraint.student_id_b,
                    kind=PairConstraintKind(constraint.kind),
                    strength=constraint.strength,
                )
                for constraint in model.pair_constraints
            ],
            planning_profile=planning_profile,
        )

    async def get_by_id(self, *, draft_id: UUID) -> PlanDraft | None:
        model = await self._session.get(PlanDraftModel, draft_id)
        return self._to_draft(model) if model else None

    async def get_workspace(self, *, draft_id: UUID) -> DraftWorkspace | None:
        result = await self._session.execute(
            select(PlanDraftModel)
            .options(
                selectinload(PlanDraftModel.groups),
                selectinload(PlanDraftModel.group_assignments),
                selectinload(PlanDraftModel.seat_assignments),
                selectinload(PlanDraftModel.student_planning_meta),
                selectinload(PlanDraftModel.pair_constraints),
                selectinload(PlanDraftModel.planning_profile),
            )
            .where(PlanDraftModel.id == draft_id)
        )
        model = result.scalar_one_or_none()
        return self._to_workspace(model) if model else None

    async def list_by_owner(self, *, owner_user_id: UUID) -> list[PlanDraft]:
        result = await self._session.execute(
            select(PlanDraftModel)
            .where(PlanDraftModel.owner_user_id == owner_user_id)
            .order_by(PlanDraftModel.updated_at.desc())
        )
        return [self._to_draft(model) for model in result.scalars().all()]

    async def save(self, *, draft: PlanDraft) -> None:
        model = await self._session.get(PlanDraftModel, draft.id)
        if model:
            model.roster_id = draft.roster_id
            model.template_id = draft.template_id
            model.lesson_mode_id = draft.lesson_mode_id
            model.revision = draft.revision
            model.engine_metadata = (
                draft.engine_metadata.model_dump(mode="json") if draft.engine_metadata else None
            )
            model.updated_at = draft.updated_at
        else:
            model = PlanDraftModel(
                id=draft.id,
                owner_user_id=draft.owner_user_id,
                roster_id=draft.roster_id,
                template_id=draft.template_id,
                lesson_mode_id=draft.lesson_mode_id,
                revision=draft.revision,
                engine_metadata=(
                    draft.engine_metadata.model_dump(mode="json") if draft.engine_metadata else None
                ),
                created_at=draft.created_at,
                updated_at=draft.updated_at,
            )
            self._session.add(model)
        await self._session.flush()

    async def save_workspace(self, *, workspace: DraftWorkspace) -> None:
        draft = workspace.draft
        model = await self._session.get(
            PlanDraftModel,
            draft.id,
            options=(
                selectinload(PlanDraftModel.groups),
                selectinload(PlanDraftModel.group_assignments),
                selectinload(PlanDraftModel.seat_assignments),
                selectinload(PlanDraftModel.student_planning_meta),
                selectinload(PlanDraftModel.pair_constraints),
                selectinload(PlanDraftModel.planning_profile),
            ),
        )
        if model is None:
            model = PlanDraftModel(
                id=draft.id,
                owner_user_id=draft.owner_user_id,
                roster_id=draft.roster_id,
                template_id=draft.template_id,
                lesson_mode_id=draft.lesson_mode_id,
                revision=draft.revision,
                engine_metadata=(
                    draft.engine_metadata.model_dump(mode="json") if draft.engine_metadata else None
                ),
                created_at=draft.created_at,
                updated_at=draft.updated_at,
            )
            self._session.add(model)
        else:
            model.roster_id = draft.roster_id
            model.template_id = draft.template_id
            model.lesson_mode_id = draft.lesson_mode_id
            model.revision = draft.revision
            model.engine_metadata = (
                draft.engine_metadata.model_dump(mode="json") if draft.engine_metadata else None
            )
            model.updated_at = draft.updated_at

        await self._replace_related_collection(
            model=model,
            attribute_name="groups",
            new_items=[
                DraftGroupModel(group_id=group.id, name=group.name, sort_order=group.sort_order)
                for group in workspace.groups
            ],
        )
        await self._replace_related_collection(
            model=model,
            attribute_name="group_assignments",
            new_items=[
                GroupAssignmentModel(student_id=assignment.student_id, group_id=assignment.group_id)
                for assignment in workspace.group_assignments
            ],
        )
        await self._replace_related_collection(
            model=model,
            attribute_name="seat_assignments",
            new_items=[
                SeatAssignmentModel(student_id=assignment.student_id, seat_id=assignment.seat_id)
                for assignment in workspace.seat_assignments
            ],
        )
        await self._replace_related_collection(
            model=model,
            attribute_name="student_planning_meta",
            new_items=[
                StudentPlanningMetaModel(
                    student_id=meta.student_id,
                    teacher_proximity=meta.teacher_proximity,
                    independent_focus_support=meta.independent_focus_support,
                    stability_preference=meta.stability_preference,
                    preferred_zone=meta.preferred_zone,
                    avoid_zone=meta.avoid_zone,
                    notes=meta.notes,
                )
                for meta in workspace.student_planning_meta
            ],
        )
        await self._replace_related_collection(
            model=model,
            attribute_name="pair_constraints",
            new_items=[
                PairConstraintModel(
                    student_id_a=constraint.student_id_a,
                    student_id_b=constraint.student_id_b,
                    kind=constraint.kind.value,
                    strength=constraint.strength,
                )
                for constraint in workspace.pair_constraints
            ],
        )
        self._upsert_planning_profile(model=model, profile=workspace.planning_profile)
        await self._session.flush()

    async def delete(self, *, draft_id: UUID) -> None:
        await self._session.execute(delete(PlanDraftModel).where(PlanDraftModel.id == draft_id))
        await self._session.flush()


class PostgreSQLArrangementSnapshotRepository(ArrangementSnapshotRepositoryProtocol):
    """Persist immutable arrangement snapshots in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_domain(self, model: ArrangementSnapshotModel) -> ArrangementSnapshot:
        return ArrangementSnapshot(
            id=model.id,
            owner_user_id=model.owner_user_id,
            source_draft_id=model.source_draft_id,
            lesson_mode_id=model.lesson_mode_id,
            snapshot_schema_version=model.snapshot_schema_version,
            payload=model.payload,
            created_at=model.created_at,
        )

    async def get_by_id(self, *, snapshot_id: UUID) -> ArrangementSnapshot | None:
        model = await self._session.get(ArrangementSnapshotModel, snapshot_id)
        return self._to_domain(model) if model else None

    async def list_by_owner(self, *, owner_user_id: UUID) -> list[ArrangementSnapshot]:
        result = await self._session.execute(
            select(ArrangementSnapshotModel)
            .where(ArrangementSnapshotModel.owner_user_id == owner_user_id)
            .order_by(ArrangementSnapshotModel.created_at.desc())
        )
        return [self._to_domain(model) for model in result.scalars().all()]

    async def save(self, *, snapshot: ArrangementSnapshot) -> None:
        self._session.add(
            ArrangementSnapshotModel(
                id=snapshot.id,
                owner_user_id=snapshot.owner_user_id,
                source_draft_id=snapshot.source_draft_id,
                lesson_mode_id=snapshot.lesson_mode_id,
                snapshot_schema_version=snapshot.snapshot_schema_version,
                payload=snapshot.payload,
                created_at=snapshot.created_at,
            )
        )
        await self._session.flush()


class PostgreSQLRosterRepository(RosterRepositoryProtocol):
    """Persist classroom planner rosters in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, *, roster_id: UUID) -> Roster | None:
        result = await self._session.execute(select(RosterModel).where(RosterModel.id == roster_id))
        model = result.scalar_one_or_none()
        if not model:
            return None
        return Roster(
            id=model.id,
            owner_user_id=model.owner_user_id,
            name=model.name,
            students=[Student(id=s["id"], display_name=s["display_name"]) for s in model.students],
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def list_by_owner(self, *, owner_user_id: UUID) -> list[Roster]:
        result = await self._session.execute(
            select(RosterModel)
            .where(RosterModel.owner_user_id == owner_user_id)
            .order_by(RosterModel.name)
        )
        return [
            Roster(
                id=model.id,
                owner_user_id=model.owner_user_id,
                name=model.name,
                students=[
                    Student(id=s["id"], display_name=s["display_name"]) for s in model.students
                ],
                created_at=model.created_at,
                updated_at=model.updated_at,
            )
            for model in result.scalars().all()
        ]

    async def save(self, *, roster: Roster) -> None:
        model = await self._session.get(RosterModel, roster.id)
        if model:
            model.name = roster.name
            model.students = [student.model_dump() for student in roster.students]
            model.updated_at = roster.updated_at
        else:
            model = RosterModel(
                id=roster.id,
                owner_user_id=roster.owner_user_id,
                name=roster.name,
                students=[student.model_dump() for student in roster.students],
                created_at=roster.created_at,
                updated_at=roster.updated_at,
            )
            self._session.add(model)
        await self._session.flush()

    async def delete(self, *, roster_id: UUID) -> None:
        await self._session.execute(delete(RosterModel).where(RosterModel.id == roster_id))
        await self._session.flush()


class PostgreSQLRoomTemplateRepository(RoomTemplateRepositoryProtocol):
    """Persist classroom planner room templates in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, *, template_id: UUID) -> RoomTemplate | None:
        result = await self._session.execute(
            select(RoomTemplateModel).where(RoomTemplateModel.id == template_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return RoomTemplate(
            id=model.id,
            owner_user_id=model.owner_user_id,
            name=model.name,
            seats=[Seat(id=s["id"], x=s["x"], y=s["y"], zone=s.get("zone")) for s in model.seats],
            fixtures=[
                RoomFixture(
                    id=fixture["id"],
                    type=RoomFixtureType(fixture["type"]),
                    x=fixture["x"],
                    y=fixture["y"],
                    width=fixture["width"],
                    height=fixture["height"],
                    label=fixture.get("label"),
                )
                for fixture in model.fixtures
            ],
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def list_by_owner(self, *, owner_user_id: UUID) -> list[RoomTemplate]:
        result = await self._session.execute(
            select(RoomTemplateModel)
            .where(RoomTemplateModel.owner_user_id == owner_user_id)
            .order_by(RoomTemplateModel.name)
        )
        return [
            RoomTemplate(
                id=model.id,
                owner_user_id=model.owner_user_id,
                name=model.name,
                seats=[
                    Seat(id=s["id"], x=s["x"], y=s["y"], zone=s.get("zone")) for s in model.seats
                ],
                fixtures=[
                    RoomFixture(
                        id=fixture["id"],
                        type=RoomFixtureType(fixture["type"]),
                        x=fixture["x"],
                        y=fixture["y"],
                        width=fixture["width"],
                        height=fixture["height"],
                        label=fixture.get("label"),
                    )
                    for fixture in model.fixtures
                ],
                created_at=model.created_at,
                updated_at=model.updated_at,
            )
            for model in result.scalars().all()
        ]

    async def save(self, *, template: RoomTemplate) -> None:
        model = await self._session.get(RoomTemplateModel, template.id)
        if model:
            model.name = template.name
            model.seats = [seat.model_dump() for seat in template.seats]
            model.fixtures = [fixture.model_dump(mode="json") for fixture in template.fixtures]
            model.updated_at = template.updated_at
        else:
            model = RoomTemplateModel(
                id=template.id,
                owner_user_id=template.owner_user_id,
                name=template.name,
                seats=[seat.model_dump() for seat in template.seats],
                fixtures=[fixture.model_dump(mode="json") for fixture in template.fixtures],
                created_at=template.created_at,
                updated_at=template.updated_at,
            )
            self._session.add(model)
        await self._session.flush()

    async def delete(self, *, template_id: UUID) -> None:
        await self._session.execute(
            delete(RoomTemplateModel).where(RoomTemplateModel.id == template_id)
        )
        await self._session.flush()
