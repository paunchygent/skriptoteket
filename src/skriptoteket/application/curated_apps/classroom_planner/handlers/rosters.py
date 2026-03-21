"""Roster handlers for the classroom planner curated app.

This module owns teacher-managed roster CRUD flows. It keeps reusable roster
assets separate from draft-scoped planning state and enforces owner scoping plus
basic roster invariants at the application boundary.
"""

from __future__ import annotations

from collections import Counter
from uuid import UUID

from skriptoteket.domain.curated_apps.classroom_planner.models import Roster, Student
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found, validation_error
from skriptoteket.protocols.classroom_planner import (
    PlanDraftRepositoryProtocol,
    RosterRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


def _validate_students(*, students: list[Student]) -> None:
    duplicates = [
        student_id for student_id, count in Counter(s.id for s in students).items() if count > 1
    ]
    if duplicates:
        raise validation_error(
            "Student IDs must be unique within a roster.",
            details={"duplicate_student_ids": duplicates},
        )


class ListRostersHandler:
    """List rosters owned by the current user."""

    def __init__(self, rosters: RosterRepositoryProtocol) -> None:
        self._rosters = rosters

    async def handle(self, *, owner_user_id: UUID) -> list[Roster]:
        return await self._rosters.list_by_owner(owner_user_id=owner_user_id)


class GetRosterHandler:
    """Load one roster owned by the current user."""

    def __init__(self, rosters: RosterRepositoryProtocol) -> None:
        self._rosters = rosters

    async def handle(self, *, roster_id: UUID, owner_user_id: UUID) -> Roster:
        roster = await self._rosters.get_by_id(roster_id=roster_id)
        if not roster or roster.owner_user_id != owner_user_id:
            raise not_found("Roster", str(roster_id))
        return roster


class CreateRosterHandler:
    """Create a reusable roster asset."""

    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        rosters: RosterRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._rosters = rosters
        self._clock = clock
        self._id_generator = id_generator

    async def handle(self, *, owner_user_id: UUID, name: str, students: list[Student]) -> Roster:
        _validate_students(students=students)
        now = self._clock.now()
        roster = Roster(
            id=self._id_generator.new_uuid(),
            owner_user_id=owner_user_id,
            name=name,
            students=students,
            created_at=now,
            updated_at=now,
        )
        async with self._uow:
            await self._rosters.save(roster=roster)
        return roster


class UpdateRosterHandler:
    """Update a reusable roster asset."""

    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        rosters: RosterRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._rosters = rosters
        self._clock = clock

    async def handle(
        self, *, roster_id: UUID, owner_user_id: UUID, name: str, students: list[Student]
    ) -> Roster:
        _validate_students(students=students)
        roster = await self._rosters.get_by_id(roster_id=roster_id)
        if not roster or roster.owner_user_id != owner_user_id:
            raise not_found("Roster", str(roster_id))

        updated = Roster(
            id=roster.id,
            owner_user_id=roster.owner_user_id,
            name=name,
            students=students,
            created_at=roster.created_at,
            updated_at=self._clock.now(),
        )
        async with self._uow:
            await self._rosters.save(roster=updated)
        return updated


class DeleteRosterHandler:
    """Delete a reusable roster asset."""

    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        rosters: RosterRepositoryProtocol,
        drafts: PlanDraftRepositoryProtocol,
    ) -> None:
        self._uow = uow
        self._rosters = rosters
        self._drafts = drafts

    async def handle(self, *, roster_id: UUID, owner_user_id: UUID) -> None:
        roster = await self._rosters.get_by_id(roster_id=roster_id)
        if not roster or roster.owner_user_id != owner_user_id:
            raise not_found("Roster", str(roster_id))
        if await self._drafts.has_active_for_roster(
            owner_user_id=owner_user_id,
            roster_id=roster_id,
        ):
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message=(
                    "Du kan inte radera klasslistan eftersom ett aktivt utkast "
                    "fortfarande använder den."
                ),
                details={"roster_id": str(roster_id), "reason": "active_draft_dependency"},
            )

        async with self._uow:
            await self._rosters.delete(roster_id=roster_id)
