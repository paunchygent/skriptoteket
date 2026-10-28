"""Integration tests for the PostgreSQL exam guest-draft handoff ledger.

Purpose:
    Prove the claim ledger semantics against real Postgres: one claim wins per
    ``draft_id`` and reports False on every later call, including for
    different owners, and the winning
    lineage is readable back.

Relationships:
    - Exercises ``PostgreSQLExamGuestDraftHandoffRepository`` under the
      migrated schema; the sign-in handoff handler builds on these semantics
      (TASK-SKRIPT-41-02-02 P5).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.infrastructure.db.models.exam_guest_draft_handoff import (
    ExamGuestDraftHandoffModel,
)
from skriptoteket.infrastructure.repositories.exam_guest_draft_handoffs import (
    PostgreSQLExamGuestDraftHandoffRepository,
)
from tests.integration.infrastructure.repositories.exam_workspace_test_support import (
    create_owner,
)

pytestmark = pytest.mark.asyncio(loop_scope="module")

_NOW = datetime(2026, 10, 18, 16, 0, tzinfo=UTC)


def _repository(session: AsyncSession) -> PostgreSQLExamGuestDraftHandoffRepository:
    return PostgreSQLExamGuestDraftHandoffRepository(session)


async def test_claims_once_per_owner_and_draft(
    db_session: AsyncSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    owner = await create_owner(session_factory)
    repository = _repository(db_session)
    draft_id = uuid4()
    winning_lineage = uuid4()

    assert (
        await repository.claim(
            owner_user_id=owner.id, draft_id=draft_id, lineage_id=winning_lineage, now=_NOW
        )
        is True
    )
    assert (
        await repository.claim(
            owner_user_id=owner.id, draft_id=draft_id, lineage_id=uuid4(), now=_NOW
        )
        is False
    )
    assert (
        await repository.get_lineage(owner_user_id=owner.id, draft_id=draft_id) == winning_lineage
    )
    stored = (
        await db_session.execute(select(func.count()).select_from(ExamGuestDraftHandoffModel))
    ).scalar_one()
    assert stored == 1


async def test_two_owners_cannot_claim_the_same_draft_id(
    db_session: AsyncSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    first_owner = await create_owner(session_factory)
    second_owner = await create_owner(session_factory)
    repository = _repository(db_session)
    draft_id = uuid4()
    first_lineage = uuid4()
    second_lineage = uuid4()

    assert (
        await repository.claim(
            owner_user_id=first_owner.id, draft_id=draft_id, lineage_id=first_lineage, now=_NOW
        )
        is True
    )
    assert (
        await repository.claim(
            owner_user_id=second_owner.id, draft_id=draft_id, lineage_id=second_lineage, now=_NOW
        )
        is False
    )
    assert await repository.get_lineage(owner_user_id=first_owner.id, draft_id=draft_id) == (
        first_lineage
    )
    assert await repository.get_lineage(owner_user_id=second_owner.id, draft_id=draft_id) is None


async def test_unknown_draft_returns_no_lineage(
    db_session: AsyncSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    owner = await create_owner(session_factory)
    repository = _repository(db_session)

    assert await repository.get_lineage(owner_user_id=owner.id, draft_id=uuid4()) is None
