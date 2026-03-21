"""PostgreSQL repositories for classroom planner aggregates.

This module maps SQLAlchemy models to the active classroom-planner domain
models. It persists reusable teacher assets plus the mutable draft workspace
for grouping, seating, and teacher-note fundamentals.
"""

from __future__ import annotations

from datetime import datetime
from hashlib import blake2b
from uuid import UUID

from sqlalchemy import delete, exists, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassWorkspaceDraftSummary,
    DraftGroup,
    DraftWorkspace,
    GroupAssignment,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
    PlanDraftSummary,
    ResumablePlanDraft,
    RoomFixture,
    RoomFixtureType,
    RoomTemplate,
    Roster,
    Seat,
    SeatAssignment,
    Student,
    StudentPlanningMeta,
)
from skriptoteket.infrastructure.db.models.classroom_planner_plan_draft import (
    DraftGroupModel,
    GroupAssignmentModel,
    PlanDraftModel,
    SeatAssignmentModel,
    StudentPlanningMetaModel,
)
from skriptoteket.infrastructure.db.models.classroom_planner_room_template import (
    RoomTemplateModel,
)
from skriptoteket.infrastructure.db.models.classroom_planner_roster import RosterModel
from skriptoteket.protocols.classroom_planner import (
    PlanDraftRepositoryProtocol,
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
)


class PostgreSQLPlanDraftRepository(PlanDraftRepositoryProtocol):
    """Persist draft roots and fundamentals workspace state in PostgreSQL."""

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

    def _to_draft(self, model: PlanDraftModel) -> PlanDraft:
        """Map one draft ORM row to the active domain aggregate."""

        return PlanDraft(
            id=model.id,
            owner_user_id=model.owner_user_id,
            roster_id=model.roster_id,
            draft_kind=PlanDraftKind(model.draft_kind),
            template_id=model.template_id,
            status=PlanDraftStatus(model.status),
            revision=model.revision,
            last_opened_at=model.last_opened_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_workspace(self, model: PlanDraftModel) -> DraftWorkspace:
        """Map one hydrated draft ORM row to the active workspace aggregate."""

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
                    stability_preference=meta.stability_preference,
                    preferred_zone=meta.preferred_zone,
                    avoid_zone=meta.avoid_zone,
                    notes=meta.notes,
                )
                for meta in model.student_planning_meta
            ],
        )

    def _to_draft_summary(
        self,
        model: PlanDraftModel,
        *,
        template_name: str | None,
    ) -> PlanDraftSummary:
        """Map one draft row plus template label to the compact summary model."""

        return PlanDraftSummary(
            id=model.id,
            draft_kind=PlanDraftKind(model.draft_kind),
            template_id=model.template_id,
            template_name=template_name,
            status=PlanDraftStatus(model.status),
            revision=model.revision,
            last_opened_at=model.last_opened_at,
            updated_at=model.updated_at,
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

    async def get_active_by_roster_and_kind(
        self,
        *,
        owner_user_id: UUID,
        roster_id: UUID,
        draft_kind: PlanDraftKind,
    ) -> PlanDraft | None:
        result = await self._session.execute(
            select(PlanDraftModel)
            .where(
                PlanDraftModel.owner_user_id == owner_user_id,
                PlanDraftModel.roster_id == roster_id,
                PlanDraftModel.draft_kind == draft_kind.value,
                PlanDraftModel.status == PlanDraftStatus.ACTIVE.value,
            )
            .order_by(PlanDraftModel.last_opened_at.desc(), PlanDraftModel.updated_at.desc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return self._to_draft(model) if model else None

    async def acquire_roster_kind_lifecycle_lock(
        self,
        *,
        owner_user_id: UUID,
        roster_id: UUID,
        draft_kind: PlanDraftKind,
    ) -> None:
        lock_source = f"{owner_user_id}:{roster_id}:{draft_kind.value}".encode("utf-8")
        lock_key = int.from_bytes(blake2b(lock_source, digest_size=8).digest(), "big")
        lock_key &= 0x7FFFFFFFFFFFFFFF
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": lock_key},
        )

    async def get_latest_resumable(self, *, owner_user_id: UUID) -> ResumablePlanDraft | None:
        result = await self._session.execute(
            select(PlanDraftModel, RosterModel.name, RoomTemplateModel.name)
            .join(RosterModel, RosterModel.id == PlanDraftModel.roster_id)
            .outerjoin(RoomTemplateModel, RoomTemplateModel.id == PlanDraftModel.template_id)
            .where(
                PlanDraftModel.owner_user_id == owner_user_id,
                PlanDraftModel.status == PlanDraftStatus.ACTIVE.value,
            )
            .order_by(PlanDraftModel.last_opened_at.desc(), PlanDraftModel.updated_at.desc())
            .limit(1)
        )
        row = result.first()
        if row is None:
            return None
        model, roster_name, template_name = row
        return ResumablePlanDraft(
            draft=self._to_draft(model),
            roster_name=roster_name,
            template_name=template_name,
        )

    async def _get_latest_summary_for_kind_and_status(
        self,
        *,
        owner_user_id: UUID,
        roster_id: UUID,
        draft_kind: PlanDraftKind,
        status: PlanDraftStatus,
    ) -> PlanDraftSummary | None:
        """Load the latest compact summary for one class, task, and lifecycle status."""

        result = await self._session.execute(
            select(PlanDraftModel, RoomTemplateModel.name)
            .outerjoin(RoomTemplateModel, RoomTemplateModel.id == PlanDraftModel.template_id)
            .where(
                PlanDraftModel.owner_user_id == owner_user_id,
                PlanDraftModel.roster_id == roster_id,
                PlanDraftModel.draft_kind == draft_kind.value,
                PlanDraftModel.status == status.value,
            )
            .order_by(PlanDraftModel.last_opened_at.desc(), PlanDraftModel.updated_at.desc())
            .limit(1)
        )
        row = result.first()
        if row is None:
            return None
        model, template_name = row
        return self._to_draft_summary(model, template_name=template_name)

    async def _list_history_summaries_for_kind(
        self,
        *,
        owner_user_id: UUID,
        roster_id: UUID,
        draft_kind: PlanDraftKind,
        limit: int,
    ) -> list[PlanDraftSummary]:
        """Load compact history summaries for one class and task kind."""

        result = await self._session.execute(
            select(PlanDraftModel, RoomTemplateModel.name)
            .outerjoin(RoomTemplateModel, RoomTemplateModel.id == PlanDraftModel.template_id)
            .where(
                PlanDraftModel.owner_user_id == owner_user_id,
                PlanDraftModel.roster_id == roster_id,
                PlanDraftModel.draft_kind == draft_kind.value,
                PlanDraftModel.status != PlanDraftStatus.ACTIVE.value,
            )
            .order_by(PlanDraftModel.last_opened_at.desc(), PlanDraftModel.updated_at.desc())
            .limit(limit)
        )
        return [
            self._to_draft_summary(model, template_name=template_name)
            for model, template_name in result.all()
        ]

    async def get_class_workspace_draft_summary(
        self,
        *,
        owner_user_id: UUID,
        roster_id: UUID,
        history_limit_per_kind: int = 5,
    ) -> ClassWorkspaceDraftSummary:
        return ClassWorkspaceDraftSummary(
            active_grouping_draft=await self._get_latest_summary_for_kind_and_status(
                owner_user_id=owner_user_id,
                roster_id=roster_id,
                draft_kind=PlanDraftKind.GROUPING,
                status=PlanDraftStatus.ACTIVE,
            ),
            active_seating_draft=await self._get_latest_summary_for_kind_and_status(
                owner_user_id=owner_user_id,
                roster_id=roster_id,
                draft_kind=PlanDraftKind.SEATING,
                status=PlanDraftStatus.ACTIVE,
            ),
            grouping_history=await self._list_history_summaries_for_kind(
                owner_user_id=owner_user_id,
                roster_id=roster_id,
                draft_kind=PlanDraftKind.GROUPING,
                limit=history_limit_per_kind,
            ),
            seating_history=await self._list_history_summaries_for_kind(
                owner_user_id=owner_user_id,
                roster_id=roster_id,
                draft_kind=PlanDraftKind.SEATING,
                limit=history_limit_per_kind,
            ),
        )

    async def has_active_for_roster(self, *, owner_user_id: UUID, roster_id: UUID) -> bool:
        result = await self._session.execute(
            select(
                exists().where(
                    PlanDraftModel.owner_user_id == owner_user_id,
                    PlanDraftModel.roster_id == roster_id,
                    PlanDraftModel.status == PlanDraftStatus.ACTIVE.value,
                )
            )
        )
        return bool(result.scalar())

    async def has_active_for_template(self, *, owner_user_id: UUID, template_id: UUID) -> bool:
        result = await self._session.execute(
            select(
                exists().where(
                    PlanDraftModel.owner_user_id == owner_user_id,
                    PlanDraftModel.template_id == template_id,
                    PlanDraftModel.status == PlanDraftStatus.ACTIVE.value,
                )
            )
        )
        return bool(result.scalar())

    async def save(self, *, draft: PlanDraft) -> None:
        model = await self._session.get(PlanDraftModel, draft.id)
        if model:
            model.roster_id = draft.roster_id
            model.draft_kind = draft.draft_kind.value
            model.template_id = draft.template_id
            model.status = draft.status.value
            model.revision = draft.revision
            model.last_opened_at = draft.last_opened_at
            model.updated_at = draft.updated_at
        else:
            model = PlanDraftModel(
                id=draft.id,
                owner_user_id=draft.owner_user_id,
                roster_id=draft.roster_id,
                draft_kind=draft.draft_kind.value,
                template_id=draft.template_id,
                status=draft.status.value,
                revision=draft.revision,
                last_opened_at=draft.last_opened_at,
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
            ),
        )
        if model is None:
            model = PlanDraftModel(
                id=draft.id,
                owner_user_id=draft.owner_user_id,
                roster_id=draft.roster_id,
                draft_kind=draft.draft_kind.value,
                template_id=draft.template_id,
                status=draft.status.value,
                revision=draft.revision,
                last_opened_at=draft.last_opened_at,
                created_at=draft.created_at,
                updated_at=draft.updated_at,
            )
            self._session.add(model)
        else:
            model.roster_id = draft.roster_id
            model.draft_kind = draft.draft_kind.value
            model.template_id = draft.template_id
            model.status = draft.status.value
            model.revision = draft.revision
            model.last_opened_at = draft.last_opened_at
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
                    stability_preference=meta.stability_preference,
                    preferred_zone=meta.preferred_zone,
                    avoid_zone=meta.avoid_zone,
                    notes=meta.notes,
                )
                for meta in workspace.student_planning_meta
            ],
        )
        await self._session.flush()

    async def mark_status(
        self,
        *,
        draft_id: UUID,
        owner_user_id: UUID,
        status: PlanDraftStatus,
        updated_at: datetime,
    ) -> PlanDraft | None:
        model = await self._session.get(PlanDraftModel, draft_id)
        if model is None or model.owner_user_id != owner_user_id:
            return None
        model.status = status.value
        model.updated_at = updated_at
        await self._session.flush()
        return self._to_draft(model)

    async def delete(self, *, draft_id: UUID) -> None:
        await self._session.execute(delete(PlanDraftModel).where(PlanDraftModel.id == draft_id))
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
