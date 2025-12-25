from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.domain.suggestions.models import (
    SuggestionDecisionType,
    create_suggestion,
    decide_suggestion,
)
from skriptoteket.infrastructure.repositories.script_suggestion_decision_repository import (
    PostgreSQLScriptSuggestionDecisionRepository,
)
from skriptoteket.infrastructure.repositories.script_suggestion_repository import (
    PostgreSQLScriptSuggestionRepository,
)
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository

pytestmark = pytest.mark.asyncio(loop_scope="module")


async def _create_user(*, db_session: AsyncSession) -> uuid.UUID:
    now = datetime.now(timezone.utc)
    user = User(
        id=uuid.uuid4(),
        email=f"decider-{uuid.uuid4().hex[:8]}@example.com",
        role=Role.ADMIN,
        auth_provider=AuthProvider.LOCAL,
        created_at=now,
        updated_at=now,
    )
    await PostgreSQLUserRepository(db_session).create(user=user, password_hash="hash")
    await db_session.flush()
    return user.id


@pytest.mark.integration
async def test_decision_repository_create_and_list_ordering(db_session: AsyncSession) -> None:
    suggestion_repo = PostgreSQLScriptSuggestionRepository(db_session)
    decision_repo = PostgreSQLScriptSuggestionDecisionRepository(db_session)

    submitter_id = await _create_user(db_session=db_session)
    decider_id = await _create_user(db_session=db_session)

    now = datetime.now(timezone.utc)
    suggestion_id = uuid.uuid4()
    suggestion = create_suggestion(
        suggestion_id=suggestion_id,
        submitted_by_user_id=submitter_id,
        title="Suggestion",
        description="Desc",
        profession_slugs=["teacher"],
        category_slugs=["admin"],
        now=now,
    )
    await suggestion_repo.create(suggestion=suggestion)
    await db_session.flush()

    updated_1, decision_1 = decide_suggestion(
        suggestion=suggestion,
        decision_id=uuid.uuid4(),
        decided_by_user_id=decider_id,
        decision=SuggestionDecisionType.DENY,
        rationale="No",
        title=None,
        description=None,
        profession_slugs=None,
        category_slugs=None,
        created_tool_id=None,
        now=now,
    )
    await suggestion_repo.update(suggestion=updated_1)
    created_1 = await decision_repo.create(decision=decision_1)

    later = now + timedelta(seconds=1)
    updated_2, decision_2 = decide_suggestion(
        suggestion=suggestion,
        decision_id=uuid.uuid4(),
        decided_by_user_id=decider_id,
        decision=SuggestionDecisionType.DENY,
        rationale="Still no",
        title="Override title",
        description="Override desc",
        profession_slugs=["teacher"],
        category_slugs=["admin"],
        created_tool_id=None,
        now=later,
    )
    del updated_2
    created_2 = await decision_repo.create(decision=decision_2)

    decisions = await decision_repo.list_for_suggestion(suggestion_id=suggestion_id)
    assert [d.id for d in decisions] == [created_2.id, created_1.id]


@pytest.mark.integration
async def test_decision_field_verification(db_session: AsyncSession) -> None:
    """Test that all decision fields are persisted and retrievable."""
    suggestion_repo = PostgreSQLScriptSuggestionRepository(db_session)
    decision_repo = PostgreSQLScriptSuggestionDecisionRepository(db_session)

    submitter_id = await _create_user(db_session=db_session)
    decider_id = await _create_user(db_session=db_session)

    now = datetime.now(timezone.utc)
    suggestion_id = uuid.uuid4()
    suggestion = create_suggestion(
        suggestion_id=suggestion_id,
        submitted_by_user_id=submitter_id,
        title="Tool Suggestion",
        description="A tool that does something useful",
        profession_slugs=["teacher", "researcher"],
        category_slugs=["admin", "grading"],
        now=now,
    )
    await suggestion_repo.create(suggestion=suggestion)
    await db_session.flush()

    # Create decision with all text fields populated (DENY to skip tool FK requirement)
    updated, decision = decide_suggestion(
        suggestion=suggestion,
        decision_id=uuid.uuid4(),
        decided_by_user_id=decider_id,
        decision=SuggestionDecisionType.DENY,
        rationale="Not feasible at this time, but good idea!",
        title="Modified Title",
        description="Modified description with more details",
        profession_slugs=["teacher"],
        category_slugs=["grading"],
        created_tool_id=None,
        now=now,
    )
    await suggestion_repo.update(suggestion=updated)
    created = await decision_repo.create(decision=decision)

    # Verify fields on created object
    assert created.suggestion_id == suggestion_id
    assert created.decided_by_user_id == decider_id
    assert created.decision == SuggestionDecisionType.DENY
    assert created.rationale == "Not feasible at this time, but good idea!"
    assert created.title == "Modified Title"
    assert created.description == "Modified description with more details"
    assert list(created.profession_slugs) == ["teacher"]
    assert list(created.category_slugs) == ["grading"]
    assert created.created_tool_id is None
    assert created.decided_at == now

    # Verify fields persist via fetch
    decisions = await decision_repo.list_for_suggestion(suggestion_id=suggestion_id)
    assert len(decisions) == 1
    fetched = decisions[0]

    assert fetched.suggestion_id == suggestion_id
    assert fetched.decided_by_user_id == decider_id
    assert fetched.decision == SuggestionDecisionType.DENY
    assert fetched.rationale == "Not feasible at this time, but good idea!"
    assert fetched.title == "Modified Title"
    assert fetched.description == "Modified description with more details"
    assert list(fetched.profession_slugs) == ["teacher"]
    assert list(fetched.category_slugs) == ["grading"]
    assert fetched.created_tool_id is None
