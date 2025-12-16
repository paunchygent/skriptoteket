from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.domain.suggestions.models import SuggestionStatus, create_suggestion
from skriptoteket.infrastructure.repositories.script_suggestion_repository import (
    PostgreSQLScriptSuggestionRepository,
)
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.mark.integration
async def test_script_suggestion_repository(db_session: AsyncSession) -> None:
    repo = PostgreSQLScriptSuggestionRepository(db_session)
    user_repo = PostgreSQLUserRepository(db_session)
    now = datetime.now(timezone.utc)

    # 1. Create a user first (Foreign Key dependency)
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="submitter@example.com",
        role=Role.USER,
        auth_provider=AuthProvider.LOCAL,
        created_at=now,
        updated_at=now,
    )
    await user_repo.create(user=user, password_hash="hash")

    # 2. Create Suggestion
    suggestion_id = uuid.uuid4()
    suggestion = create_suggestion(
        suggestion_id=suggestion_id,
        submitted_by_user_id=user_id,
        title="My Suggestion",
        description="Do something cool",
        profession_slugs=["engineer"],
        category_slugs=["calc"],
        now=now,
    )

    # 3. Save
    await repo.create(suggestion=suggestion)
    await db_session.flush()

    # 4. Get by ID
    fetched = await repo.get_by_id(suggestion_id=suggestion_id)
    assert fetched is not None
    assert fetched.title == "My Suggestion"
    assert fetched.submitted_by_user_id == user_id

    # 5. List Pending (ordering by created_at desc, id desc)
    suggestion_id_2 = uuid.uuid4()
    later = now + timedelta(seconds=1)
    suggestion_2 = create_suggestion(
        suggestion_id=suggestion_id_2,
        submitted_by_user_id=user_id,
        title="My Suggestion 2",
        description="Do something else",
        profession_slugs=["engineer"],
        category_slugs=["calc"],
        now=later,
    )
    await repo.create(suggestion=suggestion_2)
    await db_session.flush()

    pending = await repo.list_for_review()
    assert [s.id for s in pending[:2]] == [suggestion_id_2, suggestion_id]

    # 6. Update (persist review fields)
    reviewer_id = uuid.uuid4()
    await PostgreSQLUserRepository(db_session).create(
        user=User(
            id=reviewer_id,
            email="reviewer@example.com",
            role=Role.ADMIN,
            auth_provider=AuthProvider.LOCAL,
            created_at=now,
            updated_at=now,
        ),
        password_hash="hash",
    )
    await db_session.flush()

    updated = fetched.model_copy(
        update={
            "status": SuggestionStatus.DENIED,
            "reviewed_by_user_id": reviewer_id,
            "reviewed_at": later,
            "review_rationale": "No",
            "updated_at": later,
        }
    )
    saved = await repo.update(suggestion=updated)
    assert saved.status is SuggestionStatus.DENIED

    fetched_updated = await repo.get_by_id(suggestion_id=suggestion_id)
    assert fetched_updated is not None
    assert fetched_updated.review_rationale == "No"

    # 7. Update missing raises not found
    missing = suggestion.model_copy(update={"id": uuid.uuid4()})
    with pytest.raises(DomainError) as exc_info:
        await repo.update(suggestion=missing)
    assert exc_info.value.code is ErrorCode.NOT_FOUND
