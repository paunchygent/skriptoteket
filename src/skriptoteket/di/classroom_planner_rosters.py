"""DI bindings for classroom planner roster lifecycle services.

Roster CRUD handlers, deleted-student cleanup, and the cleanup repository are
registered together so class-list lifecycle wiring stays easy to inspect.
"""

from __future__ import annotations

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.classroom_planner import (
    CreateRosterHandler,
    DeleteRosterHandler,
    GetRosterHandler,
    ListRostersHandler,
    UpdateRosterHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers import (
    roster_student_cleanup,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers.share_artifacts import (
    ClassroomPlannerShareLifecycleService,
)
from skriptoteket.infrastructure.repositories.classroom_planner_roster_students import (
    PostgreSQLRosterStudentReferenceRepository,
)
from skriptoteket.protocols.classroom_planner import (
    PlanDraftRepositoryProtocol,
    RosterRepositoryProtocol,
    RosterSmartRuleRepositoryProtocol,
    RosterStudentReferenceRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class ClassroomPlannerRosterProvider(Provider):
    """Provide roster handlers and class-list cleanup collaborators."""

    @provide(scope=Scope.REQUEST)
    def roster_student_reference_repository(
        self,
        session: AsyncSession,
    ) -> RosterStudentReferenceRepositoryProtocol:
        """Provide draft-reference cleanup for deleted roster students."""
        return PostgreSQLRosterStudentReferenceRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def roster_student_cleanup_service(
        self,
        student_references: RosterStudentReferenceRepositoryProtocol,
        smart_rules: RosterSmartRuleRepositoryProtocol,
    ) -> roster_student_cleanup.RosterStudentCleanupService:
        """Provide save-time cleanup for removed roster students."""
        return roster_student_cleanup.RosterStudentCleanupService(
            student_references=student_references,
            smart_rules=smart_rules,
        )

    @provide(scope=Scope.REQUEST)
    def list_rosters_handler(self, rosters: RosterRepositoryProtocol) -> ListRostersHandler:
        """Provide the roster listing handler."""
        return ListRostersHandler(rosters=rosters)

    @provide(scope=Scope.REQUEST)
    def get_roster_handler(self, rosters: RosterRepositoryProtocol) -> GetRosterHandler:
        """Provide the roster lookup handler."""
        return GetRosterHandler(rosters=rosters)

    @provide(scope=Scope.REQUEST)
    def create_roster_handler(
        self,
        uow: UnitOfWorkProtocol,
        rosters: RosterRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> CreateRosterHandler:
        """Provide the roster creation handler."""
        return CreateRosterHandler(
            uow=uow,
            rosters=rosters,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def update_roster_handler(
        self,
        uow: UnitOfWorkProtocol,
        rosters: RosterRepositoryProtocol,
        student_cleanup: roster_student_cleanup.RosterStudentCleanupService,
        clock: ClockProtocol,
    ) -> UpdateRosterHandler:
        """Provide the roster update handler."""
        return UpdateRosterHandler(
            uow=uow,
            rosters=rosters,
            student_cleanup=student_cleanup,
            clock=clock,
        )

    @provide(scope=Scope.REQUEST)
    def delete_roster_handler(
        self,
        uow: UnitOfWorkProtocol,
        rosters: RosterRepositoryProtocol,
        drafts: PlanDraftRepositoryProtocol,
        share_lifecycle: ClassroomPlannerShareLifecycleService,
    ) -> DeleteRosterHandler:
        """Provide the roster deletion handler."""
        return DeleteRosterHandler(
            uow=uow,
            rosters=rosters,
            drafts=drafts,
            share_lifecycle=share_lifecycle,
        )
