from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.identity.models import AuthProvider, Role, Session, User
from skriptoteket.infrastructure.db.models.tool import ToolModel
from skriptoteket.infrastructure.db.models.tool_maintainer import ToolMaintainerModel
from skriptoteket.infrastructure.repositories.session_repository import PostgreSQLSessionRepository
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository

pytestmark = pytest.mark.asyncio(loop_scope="module")


async def _login_as_user(*, client: AsyncClient, db_session: AsyncSession) -> User:
    """Log in as basic USER (not contributor)."""
    user_repo = PostgreSQLUserRepository(db_session)
    session_repo = PostgreSQLSessionRepository(db_session)

    now = datetime.now(timezone.utc)
    user = User(
        id=uuid.uuid4(),
        email="user@example.com",
        role=Role.USER,
        auth_provider=AuthProvider.LOCAL,
        created_at=now,
        updated_at=now,
    )
    await user_repo.create(user=user, password_hash="hash")

    session_id = uuid.uuid4()
    session = Session(
        id=session_id,
        user_id=user.id,
        csrf_token="csrf",
        created_at=now,
        expires_at=now + timedelta(days=1),
    )
    await session_repo.create(session=session)
    await db_session.flush()

    client.cookies.set("skriptoteket_session", str(session_id))
    return user


async def _login_as_contributor(*, client: AsyncClient, db_session: AsyncSession) -> User:
    user_repo = PostgreSQLUserRepository(db_session)
    session_repo = PostgreSQLSessionRepository(db_session)

    now = datetime.now(timezone.utc)
    contributor = User(
        id=uuid.uuid4(),
        email="contributor@example.com",
        role=Role.CONTRIBUTOR,
        auth_provider=AuthProvider.LOCAL,
        created_at=now,
        updated_at=now,
    )
    await user_repo.create(user=contributor, password_hash="hash")

    session_id = uuid.uuid4()
    session = Session(
        id=session_id,
        user_id=contributor.id,
        csrf_token="csrf",
        created_at=now,
        expires_at=now + timedelta(days=1),
    )
    await session_repo.create(session=session)
    await db_session.flush()

    client.cookies.set("skriptoteket_session", str(session_id))
    return contributor


async def _create_tool_with_maintainer(
    *, db_session: AsyncSession, maintainer_id: uuid.UUID
) -> ToolModel:
    now = datetime.now(timezone.utc)
    model = ToolModel(
        id=uuid.uuid4(),
        slug="my-tool",
        title="My Tool",
        summary="A tool I maintain",
        is_published=True,
        active_version_id=None,
        created_at=now,
        updated_at=now,
    )
    db_session.add(model)
    await db_session.flush()

    maintainer = ToolMaintainerModel(tool_id=model.id, user_id=maintainer_id)
    db_session.add(maintainer)
    await db_session.flush()

    return model


@pytest.mark.integration
async def test_my_tools_requires_contributor(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Basic users should not be able to access /my-tools."""
    await _login_as_user(client=client, db_session=db_session)

    response = await client.get("/my-tools", follow_redirects=False)

    assert response.status_code in (302, 303, 403)


@pytest.mark.integration
async def test_my_tools_shows_empty_state_when_no_tools(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await _login_as_contributor(client=client, db_session=db_session)

    response = await client.get("/my-tools")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    # Should show empty state message
    assert "Inga verktyg" in response.text or "inga verktyg" in response.text.lower()


@pytest.mark.integration
async def test_my_tools_lists_tools_where_user_is_maintainer(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    contributor = await _login_as_contributor(client=client, db_session=db_session)
    tool = await _create_tool_with_maintainer(db_session=db_session, maintainer_id=contributor.id)

    response = await client.get("/my-tools")

    assert response.status_code == 200
    assert tool.title in response.text
    assert f"/admin/tools/{tool.id}" in response.text
