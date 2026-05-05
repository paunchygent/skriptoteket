"""DI bindings for classroom planner smart-rule handlers.

Smart-rule read/write handlers sit in a focused provider because rule
validation spans rosters, classroom templates, and roster-owned rule storage.
"""

from __future__ import annotations

from dishka import Provider, Scope, provide

from skriptoteket.application.curated_apps.classroom_planner import (
    GetRosterSmartRulesHandler,
    PatchRosterSmartRulesHandler,
)
from skriptoteket.protocols.classroom_planner import (
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
    RosterSmartRuleRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class ClassroomPlannerSmartRuleProvider(Provider):
    """Provide roster smart-rule application handlers."""

    @provide(scope=Scope.REQUEST)
    def get_roster_smart_rules_handler(
        self,
        rosters: RosterRepositoryProtocol,
        smart_rules: RosterSmartRuleRepositoryProtocol,
    ) -> GetRosterSmartRulesHandler:
        """Provide the roster smart-rule lookup handler."""
        return GetRosterSmartRulesHandler(rosters=rosters, smart_rules=smart_rules)

    @provide(scope=Scope.REQUEST)
    def patch_roster_smart_rules_handler(
        self,
        uow: UnitOfWorkProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
        smart_rules: RosterSmartRuleRepositoryProtocol,
    ) -> PatchRosterSmartRulesHandler:
        """Provide the roster smart-rule update handler."""
        return PatchRosterSmartRulesHandler(
            uow=uow,
            rosters=rosters,
            templates=templates,
            smart_rules=smart_rules,
        )
