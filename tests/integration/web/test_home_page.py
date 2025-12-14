from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.identity.models import AuthProvider, Role, Session, User
from skriptoteket.infrastructure.repositories.session_repository import PostgreSQLSessionRepository
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.mark.integration
async def test_home_page_unauthenticated_redirects(client: AsyncClient) -> None:
    response = await client.get("/", follow_redirects=False)
    # The dependencies/require_user usually raises HTTPException(401) or Redirects.
    # Since it's a web app, it likely redirects.
    assert response.status_code in {302, 303, 307}
    assert "/login" in response.headers["location"]


@pytest.mark.integration
async def test_home_page_authenticated(client: AsyncClient, db_session: AsyncSession) -> None:
    user_repo = PostgreSQLUserRepository(db_session)
    session_repo = PostgreSQLSessionRepository(db_session)
    now = datetime.now(timezone.utc)

    # 1. Create User
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="user@example.com",
        role=Role.USER,
        auth_provider=AuthProvider.LOCAL,
        created_at=now,
        updated_at=now,
    )
    await user_repo.create(user=user, password_hash="hash")

    # 2. Create Session
    session_id = uuid.uuid4()
    session = Session(
        id=session_id,
        user_id=user_id,
        csrf_token="csrf",
        created_at=now,
        expires_at=now + timedelta(days=1),
    )
    await session_repo.create(session=session)
    # We must flush to ensure the session exists in the transaction visible to the app
    # (Since we share the session object, flush is enough).
    # But wait, we modified the conftest to use one db_session object.
    # So flushing here should make it visible to the app running in the same process/loop.
    await db_session.flush()

    # 3. Set Cookie
    client.cookies.set("skriptoteket_session", str(session_id))

    # 4. Get /
    response = await client.get("/")
    assert response.status_code == 200
    assert "Skriptoteket" in response.text
