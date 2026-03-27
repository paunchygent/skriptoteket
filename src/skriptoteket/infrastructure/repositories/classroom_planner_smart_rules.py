"""PostgreSQL repository for roster-owned classroom planner smart rules.

This module persists the class-global smart-rule set separately from
draft-local workspace state so multiple drafts for one roster can share the
same teacher-authored relationship and near-teacher rules with optimistic
concurrency at the roster aggregate boundary.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    RelationshipKind,
    RelationshipRule,
    RosterSmartRules,
    StudentSeatingPreference,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.db.models.classroom_planner_roster_smart_rule import (
    RosterRelationshipRuleModel,
    RosterSeatingPreferenceModel,
    RosterSmartRuleSetModel,
)
from skriptoteket.protocols.classroom_planner import RosterSmartRuleRepositoryProtocol


class PostgreSQLRosterSmartRuleRepository(RosterSmartRuleRepositoryProtocol):
    """Persist roster-owned smart rules in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_roster_id(self, *, roster_id: UUID) -> RosterSmartRules:
        root_result = await self._session.execute(
            select(RosterSmartRuleSetModel).where(RosterSmartRuleSetModel.roster_id == roster_id)
        )
        root = root_result.scalar_one_or_none()
        if root is None:
            return RosterSmartRules(roster_id=roster_id, revision=0)

        seating_result = await self._session.execute(
            select(RosterSeatingPreferenceModel)
            .where(RosterSeatingPreferenceModel.roster_id == roster_id)
            .order_by(RosterSeatingPreferenceModel.student_id)
        )
        relationship_result = await self._session.execute(
            select(RosterRelationshipRuleModel)
            .where(RosterRelationshipRuleModel.roster_id == roster_id)
            .order_by(RosterRelationshipRuleModel.rule_id)
        )
        return RosterSmartRules(
            roster_id=roster_id,
            revision=root.revision,
            seating_preferences=[
                StudentSeatingPreference(
                    student_id=model.student_id,
                    near_teacher=model.near_teacher,
                )
                for model in seating_result.scalars().all()
            ],
            relationship_rules=[
                RelationshipRule(
                    id=model.rule_id,
                    kind=RelationshipKind(model.kind),
                    student_ids=model.student_ids,
                )
                for model in relationship_result.scalars().all()
            ],
        )

    async def save(
        self,
        *,
        rules: RosterSmartRules,
        expected_revision: int,
    ) -> RosterSmartRules:
        next_revision = expected_revision + 1
        if expected_revision == 0:
            insert_result = await self._session.execute(
                insert(RosterSmartRuleSetModel)
                .values(
                    roster_id=rules.roster_id,
                    revision=next_revision,
                )
                .on_conflict_do_nothing(index_elements=["roster_id"])
                .returning(RosterSmartRuleSetModel.revision)
            )
            persisted_revision = insert_result.scalar_one_or_none()
            if persisted_revision is None:
                # Repair/backfill flows can create a legitimate root row at revision 0.
                # The first teacher edit must therefore be able to advance that row to 1
                # rather than reporting a false conflict.
                update_result = await self._session.execute(
                    update(RosterSmartRuleSetModel)
                    .where(
                        RosterSmartRuleSetModel.roster_id == rules.roster_id,
                        RosterSmartRuleSetModel.revision == expected_revision,
                    )
                    .values(revision=next_revision, updated_at=func.now())
                    .returning(RosterSmartRuleSetModel.revision)
                )
                persisted_revision = update_result.scalar_one_or_none()
        else:
            update_result = await self._session.execute(
                update(RosterSmartRuleSetModel)
                .where(
                    RosterSmartRuleSetModel.roster_id == rules.roster_id,
                    RosterSmartRuleSetModel.revision == expected_revision,
                )
                .values(revision=next_revision, updated_at=func.now())
                .returning(RosterSmartRuleSetModel.revision)
            )
            persisted_revision = update_result.scalar_one_or_none()

        if persisted_revision is None:
            current_rules = await self.get_by_roster_id(roster_id=rules.roster_id)
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message=(
                    "Roster smart-rule revision mismatch. "
                    f"Expected {expected_revision}, got {current_rules.revision}."
                ),
            )

        await self._session.execute(
            delete(RosterSeatingPreferenceModel).where(
                RosterSeatingPreferenceModel.roster_id == rules.roster_id
            )
        )
        await self._session.execute(
            delete(RosterRelationshipRuleModel).where(
                RosterRelationshipRuleModel.roster_id == rules.roster_id
            )
        )
        await self._session.flush()

        self._session.add_all(
            [
                RosterSeatingPreferenceModel(
                    roster_id=rules.roster_id,
                    student_id=preference.student_id,
                    near_teacher=preference.near_teacher,
                )
                for preference in rules.seating_preferences
            ]
        )
        self._session.add_all(
            [
                RosterRelationshipRuleModel(
                    roster_id=rules.roster_id,
                    rule_id=rule.id,
                    kind=rule.kind.value,
                    student_ids=rule.student_ids,
                )
                for rule in rules.relationship_rules
            ]
        )
        await self._session.flush()
        return rules.model_copy(update={"revision": persisted_revision})
