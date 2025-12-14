from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.domain.suggestions.models import create_suggestion
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

    # 5. List Pending
    pending = await repo.list_for_review()
    assert len(pending) == 1
    assert pending[0].id == suggestion_id
