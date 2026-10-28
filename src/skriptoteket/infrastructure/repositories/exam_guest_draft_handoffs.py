"""SQLAlchemy handoff ledger repository for exam workspace guest drafts.

Purpose:
    Claim a guest draft exactly once per ``draft_id`` so the
    sign-in handoff creates the exam in Mina filer exactly once
    (TASK-SKRIPT-41-02-02 P5).

Relationships:
    - Implements `ExamGuestDraftHandoffRepositoryProtocol`.
    - Mirrors the `INSERT ... ON CONFLICT DO NOTHING` ledger idiom of
      `PostgreSQLClassroomPlannerGuestUpgradeRepository`.
    - A concurrent claim of the same key blocks on the primary key until the
      first transaction commits and then inserts nothing.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.infrastructure.db.models.exam_guest_draft_handoff import (
    ExamGuestDraftHandoffModel,
)
from skriptoteket.protocols.exam_workspace_guest_drafts import (
    ExamGuestDraftHandoffRepositoryProtocol,
)


class PostgreSQLExamGuestDraftHandoffRepository(ExamGuestDraftHandoffRepositoryProtocol):
    """Persist and read one-time exam guest-draft handoff facts."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def claim(
        self,
        *,
        owner_user_id: UUID,
        draft_id: UUID,
        lineage_id: UUID,
        now: datetime,
    ) -> bool:
        result = await self._session.execute(
            insert(ExamGuestDraftHandoffModel)
            .values(
                owner_user_id=owner_user_id,
                draft_id=draft_id,
                lineage_id=lineage_id,
                created_at=now,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    ExamGuestDraftHandoffModel.draft_id,
                ]
            )
            .returning(ExamGuestDraftHandoffModel.owner_user_id)
        )
        return result.scalar_one_or_none() is not None

    async def get_lineage(self, *, owner_user_id: UUID, draft_id: UUID) -> UUID | None:
        result = await self._session.execute(
            select(ExamGuestDraftHandoffModel.lineage_id).where(
                ExamGuestDraftHandoffModel.owner_user_id == owner_user_id,
                ExamGuestDraftHandoffModel.draft_id == draft_id,
            )
        )
        return result.scalar_one_or_none()
