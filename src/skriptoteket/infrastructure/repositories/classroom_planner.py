from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    GroupAssignment,
    PlanDraft,
    RoomTemplate,
    Roster,
    Seat,
    SeatAssignment,
    Student,
)
from skriptoteket.infrastructure.db.models.classroom_planner_plan_draft import (
    GroupAssignmentModel,
    PlanDraftModel,
    SeatAssignmentModel,
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
    """PostgreSQL repository for classroom planner plan drafts."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_domain(self, model: PlanDraftModel) -> PlanDraft:
        return PlanDraft(
            id=model.id,
            owner_user_id=model.owner_user_id,
            roster_id=model.roster_id,
            template_id=model.template_id,
            lesson_mode_id=model.lesson_mode_id,
            revision=model.revision,
            group_count=model.group_count,
            group_assignments=[
                GroupAssignment(student_id=ga.student_id, group_id=ga.group_id)
                for ga in model.group_assignments
            ],
            seat_assignments=[
                SeatAssignment(student_id=sa.student_id, seat_id=sa.seat_id)
                for sa in model.seat_assignments
            ],
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def get_by_id(self, *, draft_id: UUID) -> PlanDraft | None:
        result = await self._session.execute(
            select(PlanDraftModel).where(PlanDraftModel.id == draft_id)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def list_by_owner(self, *, owner_user_id: UUID) -> list[PlanDraft]:
        result = await self._session.execute(
            select(PlanDraftModel)
            .where(PlanDraftModel.owner_user_id == owner_user_id)
            .order_by(PlanDraftModel.updated_at.desc())
        )
        return [self._to_domain(model) for model in result.scalars().all()]

    async def save(self, *, draft: PlanDraft) -> None:
        model = await self._session.get(PlanDraftModel, draft.id)
        if model:
            model.roster_id = draft.roster_id
            model.template_id = draft.template_id
            model.lesson_mode_id = draft.lesson_mode_id
            model.revision = draft.revision
            model.group_count = draft.group_count
            model.updated_at = draft.updated_at

            # Update assignments (replace all for simplicity in Slice 1, cascading handles cleanup)
            model.group_assignments = [
                GroupAssignmentModel(student_id=ga.student_id, group_id=ga.group_id)
                for ga in draft.group_assignments
            ]
            model.seat_assignments = [
                SeatAssignmentModel(student_id=sa.student_id, seat_id=sa.seat_id)
                for sa in draft.seat_assignments
            ]
        else:
            model = PlanDraftModel(
                id=draft.id,
                owner_user_id=draft.owner_user_id,
                roster_id=draft.roster_id,
                template_id=draft.template_id,
                lesson_mode_id=draft.lesson_mode_id,
                revision=draft.revision,
                group_count=draft.group_count,
                group_assignments=[
                    GroupAssignmentModel(student_id=ga.student_id, group_id=ga.group_id)
                    for ga in draft.group_assignments
                ],
                seat_assignments=[
                    SeatAssignmentModel(student_id=sa.student_id, seat_id=sa.seat_id)
                    for sa in draft.seat_assignments
                ],
                created_at=draft.created_at,
                updated_at=draft.updated_at,
            )
            self._session.add(model)
        await self._session.flush()

    async def delete(self, *, draft_id: UUID) -> None:
        await self._session.execute(delete(PlanDraftModel).where(PlanDraftModel.id == draft_id))
        await self._session.flush()


class PostgreSQLRosterRepository(RosterRepositoryProtocol):
    """PostgreSQL repository for classroom planner rosters."""

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
            model.students = [s.model_dump() for s in roster.students]
            model.updated_at = roster.updated_at
        else:
            model = RosterModel(
                id=roster.id,
                owner_user_id=roster.owner_user_id,
                name=roster.name,
                students=[s.model_dump() for s in roster.students],
                created_at=roster.created_at,
                updated_at=roster.updated_at,
            )
            self._session.add(model)
        await self._session.flush()

    async def delete(self, *, roster_id: UUID) -> None:
        await self._session.execute(delete(RosterModel).where(RosterModel.id == roster_id))
        await self._session.flush()


class PostgreSQLRoomTemplateRepository(RoomTemplateRepositoryProtocol):
    """PostgreSQL repository for classroom planner room templates."""

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
                created_at=model.created_at,
                updated_at=model.updated_at,
            )
            for model in result.scalars().all()
        ]

    async def save(self, *, template: RoomTemplate) -> None:
        model = await self._session.get(RoomTemplateModel, template.id)
        if model:
            model.name = template.name
            model.seats = [s.model_dump() for s in template.seats]
            model.updated_at = template.updated_at
        else:
            model = RoomTemplateModel(
                id=template.id,
                owner_user_id=template.owner_user_id,
                name=template.name,
                seats=[s.model_dump() for s in template.seats],
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
