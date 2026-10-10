"""DI bindings for classroom planner drafts, templates, and smart runs.

Draft lifecycle, room-template, class-summary, and smart-run handlers plus the
draft, roster, smart-rule, and room-template repositories they depend on.
"""

from __future__ import annotations

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.classroom_planner import (
    AbandonDraftHandler,
    ActivateGroupingHistoryDraftHandler,
    ActivateSeatingHistoryDraftHandler,
    ClassroomPlannerShareLifecycleService,
    CreateGroupingDraftHandler,
    CreateRoomTemplateHandler,
    CreateSeatingDraftHandler,
    DeleteHistoricGroupingDraftHandler,
    DeleteHistoricSeatingDraftHandler,
    DeleteRoomTemplateHandler,
    GetClassWorkspaceSummaryHandler,
    GetDraftHandler,
    GetDraftWorkspaceHandler,
    GetResumableDraftHandler,
    GetRoomTemplateHandler,
    ListRoomTemplatesHandler,
    PatchDraftHandler,
    RedoDraftHandler,
    ResolveDraftHandler,
    RunPublicSmartGroupingHandler,
    RunPublicSmartSeatingHandler,
    RunSmartGroupingHandler,
    RunSmartSeatingHandler,
    UndoDraftHandler,
    UpdateRoomTemplateHandler,
)
from skriptoteket.infrastructure.repositories.classroom_planner import (
    PostgreSQLPlanDraftRepository,
    PostgreSQLRoomTemplateRepository,
    PostgreSQLRosterRepository,
)
from skriptoteket.infrastructure.repositories.classroom_planner_smart_rules import (
    PostgreSQLRosterSmartRuleRepository,
)
from skriptoteket.protocols.classroom_planner import (
    GroupingExportCheckpointRepositoryProtocol,
    PlanDraftRepositoryProtocol,
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
    RosterSmartRuleRepositoryProtocol,
    SeatingExportCheckpointRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class ClassroomPlannerDraftProvider(Provider):
    """Provide classroom planner draft handlers and their repositories."""

    @provide(scope=Scope.REQUEST)
    def list_room_templates_handler(
        self, templates: RoomTemplateRepositoryProtocol
    ) -> ListRoomTemplatesHandler:
        return ListRoomTemplatesHandler(templates=templates)

    @provide(scope=Scope.REQUEST)
    def get_room_template_handler(
        self, templates: RoomTemplateRepositoryProtocol
    ) -> GetRoomTemplateHandler:
        return GetRoomTemplateHandler(templates=templates)

    @provide(scope=Scope.REQUEST)
    def create_room_template_handler(
        self,
        uow: UnitOfWorkProtocol,
        templates: RoomTemplateRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> CreateRoomTemplateHandler:
        return CreateRoomTemplateHandler(
            uow=uow, templates=templates, clock=clock, id_generator=id_generator
        )

    @provide(scope=Scope.REQUEST)
    def update_room_template_handler(
        self,
        uow: UnitOfWorkProtocol,
        templates: RoomTemplateRepositoryProtocol,
        clock: ClockProtocol,
    ) -> UpdateRoomTemplateHandler:
        return UpdateRoomTemplateHandler(uow=uow, templates=templates, clock=clock)

    @provide(scope=Scope.REQUEST)
    def delete_room_template_handler(
        self,
        uow: UnitOfWorkProtocol,
        templates: RoomTemplateRepositoryProtocol,
        drafts: PlanDraftRepositoryProtocol,
        share_lifecycle: ClassroomPlannerShareLifecycleService,
    ) -> DeleteRoomTemplateHandler:
        return DeleteRoomTemplateHandler(
            uow=uow,
            templates=templates,
            drafts=drafts,
            share_lifecycle=share_lifecycle,
        )

    @provide(scope=Scope.REQUEST)
    def get_draft_handler(self, drafts: PlanDraftRepositoryProtocol) -> GetDraftHandler:
        return GetDraftHandler(drafts=drafts)

    @provide(scope=Scope.REQUEST)
    def get_class_workspace_summary_handler(
        self,
        rosters: RosterRepositoryProtocol,
        drafts: PlanDraftRepositoryProtocol,
    ) -> GetClassWorkspaceSummaryHandler:
        return GetClassWorkspaceSummaryHandler(rosters=rosters, drafts=drafts)

    @provide(scope=Scope.REQUEST)
    def resolve_draft_handler(
        self,
        uow: UnitOfWorkProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
        drafts: PlanDraftRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> ResolveDraftHandler:
        return ResolveDraftHandler(
            uow=uow,
            rosters=rosters,
            templates=templates,
            drafts=drafts,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def create_grouping_draft_handler(
        self,
        uow: UnitOfWorkProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
        drafts: PlanDraftRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> CreateGroupingDraftHandler:
        return CreateGroupingDraftHandler(
            uow=uow,
            rosters=rosters,
            templates=templates,
            drafts=drafts,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def activate_grouping_history_draft_handler(
        self,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
        clock: ClockProtocol,
    ) -> ActivateGroupingHistoryDraftHandler:
        return ActivateGroupingHistoryDraftHandler(uow=uow, drafts=drafts, clock=clock)

    @provide(scope=Scope.REQUEST)
    def delete_historic_grouping_draft_handler(
        self,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
        share_lifecycle: ClassroomPlannerShareLifecycleService,
    ) -> DeleteHistoricGroupingDraftHandler:
        return DeleteHistoricGroupingDraftHandler(
            uow=uow,
            drafts=drafts,
            share_lifecycle=share_lifecycle,
        )

    @provide(scope=Scope.REQUEST)
    def create_seating_draft_handler(
        self,
        uow: UnitOfWorkProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
        drafts: PlanDraftRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> CreateSeatingDraftHandler:
        return CreateSeatingDraftHandler(
            uow=uow,
            rosters=rosters,
            templates=templates,
            drafts=drafts,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def activate_seating_history_draft_handler(
        self,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
        clock: ClockProtocol,
    ) -> ActivateSeatingHistoryDraftHandler:
        return ActivateSeatingHistoryDraftHandler(uow=uow, drafts=drafts, clock=clock)

    @provide(scope=Scope.REQUEST)
    def delete_historic_seating_draft_handler(
        self,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
        share_lifecycle: ClassroomPlannerShareLifecycleService,
    ) -> DeleteHistoricSeatingDraftHandler:
        return DeleteHistoricSeatingDraftHandler(
            uow=uow,
            drafts=drafts,
            share_lifecycle=share_lifecycle,
        )

    @provide(scope=Scope.REQUEST)
    def undo_draft_handler(
        self,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
    ) -> UndoDraftHandler:
        return UndoDraftHandler(uow=uow, drafts=drafts)

    @provide(scope=Scope.REQUEST)
    def redo_draft_handler(
        self,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
    ) -> RedoDraftHandler:
        return RedoDraftHandler(uow=uow, drafts=drafts)

    @provide(scope=Scope.REQUEST)
    def get_resumable_draft_handler(
        self, drafts: PlanDraftRepositoryProtocol
    ) -> GetResumableDraftHandler:
        return GetResumableDraftHandler(drafts=drafts)

    @provide(scope=Scope.REQUEST)
    def abandon_draft_handler(
        self,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
        clock: ClockProtocol,
    ) -> AbandonDraftHandler:
        return AbandonDraftHandler(uow=uow, drafts=drafts, clock=clock)

    @provide(scope=Scope.REQUEST)
    def get_draft_workspace_handler(
        self,
        drafts: PlanDraftRepositoryProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
        smart_rules: RosterSmartRuleRepositoryProtocol,
    ) -> GetDraftWorkspaceHandler:
        return GetDraftWorkspaceHandler(
            drafts=drafts,
            rosters=rosters,
            templates=templates,
            smart_rules=smart_rules,
        )

    @provide(scope=Scope.REQUEST)
    def patch_draft_handler(
        self,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
        clock: ClockProtocol,
    ) -> PatchDraftHandler:
        return PatchDraftHandler(
            uow=uow,
            drafts=drafts,
            rosters=rosters,
            templates=templates,
            clock=clock,
        )

    @provide(scope=Scope.REQUEST)
    def run_smart_seating_handler(
        self,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
        smart_rules: RosterSmartRuleRepositoryProtocol,
        checkpoints: SeatingExportCheckpointRepositoryProtocol,
        clock: ClockProtocol,
    ) -> RunSmartSeatingHandler:
        return RunSmartSeatingHandler(
            uow=uow,
            drafts=drafts,
            rosters=rosters,
            templates=templates,
            smart_rules=smart_rules,
            checkpoints=checkpoints,
            clock=clock,
        )

    @provide(scope=Scope.REQUEST)
    def run_smart_grouping_handler(
        self,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
        smart_rules: RosterSmartRuleRepositoryProtocol,
        grouping_checkpoints: GroupingExportCheckpointRepositoryProtocol,
        seating_checkpoints: SeatingExportCheckpointRepositoryProtocol,
        clock: ClockProtocol,
    ) -> RunSmartGroupingHandler:
        return RunSmartGroupingHandler(
            uow=uow,
            drafts=drafts,
            rosters=rosters,
            templates=templates,
            smart_rules=smart_rules,
            grouping_checkpoints=grouping_checkpoints,
            seating_checkpoints=seating_checkpoints,
            clock=clock,
        )

    @provide(scope=Scope.REQUEST)
    def run_public_smart_grouping_handler(
        self,
        clock: ClockProtocol,
    ) -> RunPublicSmartGroupingHandler:
        return RunPublicSmartGroupingHandler(clock=clock)

    @provide(scope=Scope.REQUEST)
    def run_public_smart_seating_handler(
        self,
        clock: ClockProtocol,
    ) -> RunPublicSmartSeatingHandler:
        return RunPublicSmartSeatingHandler(clock=clock)

    @provide(scope=Scope.REQUEST)
    def plan_draft_repository(self, session: AsyncSession) -> PlanDraftRepositoryProtocol:
        return PostgreSQLPlanDraftRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def roster_repository(self, session: AsyncSession) -> RosterRepositoryProtocol:
        return PostgreSQLRosterRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def roster_smart_rule_repository(
        self, session: AsyncSession
    ) -> RosterSmartRuleRepositoryProtocol:
        return PostgreSQLRosterSmartRuleRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def room_template_repository(self, session: AsyncSession) -> RoomTemplateRepositoryProtocol:
        return PostgreSQLRoomTemplateRepository(session=session)
