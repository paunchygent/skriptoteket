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
from skriptoteket.infrastructure.repositories.tool_maintainer_repository import (
    PostgreSQLToolMaintainerRepository,
)
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository

pytestmark = pytest.mark.asyncio(loop_scope="module")


async def _login_as_admin(*, client: AsyncClient, db_session: AsyncSession) -> User:
    user_repo = PostgreSQLUserRepository(db_session)
    session_repo = PostgreSQLSessionRepository(db_session)

    now = datetime.now(timezone.utc)
    admin = User(
        id=uuid.uuid4(),
        email="admin@example.com",
        role=Role.ADMIN,
        auth_provider=AuthProvider.LOCAL,
        created_at=now,
        updated_at=now,
    )
    await user_repo.create(user=admin, password_hash="hash")

    session_id = uuid.uuid4()
    session = Session(
        id=session_id,
        user_id=admin.id,
        csrf_token="csrf",
        created_at=now,
        expires_at=now + timedelta(days=1),
    )
    await session_repo.create(session=session)
    await db_session.flush()

    client.cookies.set("skriptoteket_session", str(session_id))
    return admin


async def _create_contributor(
    *, db_session: AsyncSession, email: str = "contrib@example.com"
) -> User:
    now = datetime.now(timezone.utc)
    contributor = User(
        id=uuid.uuid4(),
        email=email,
        role=Role.CONTRIBUTOR,
        auth_provider=AuthProvider.LOCAL,
        created_at=now,
        updated_at=now,
    )
    await PostgreSQLUserRepository(db_session).create(user=contributor, password_hash="hash")
    await db_session.flush()
    return contributor


async def _create_tool(*, db_session: AsyncSession) -> ToolModel:
    now = datetime.now(timezone.utc)
    model = ToolModel(
        id=uuid.uuid4(),
        slug="test-tool",
        title="Test Tool",
        summary="Summary",
        is_published=False,
        active_version_id=None,
        created_at=now,
        updated_at=now,
    )
    db_session.add(model)
    await db_session.flush()
    return model


@pytest.mark.integration
async def test_list_maintainers_returns_partial_html(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await _login_as_admin(client=client, db_session=db_session)
    tool = await _create_tool(db_session=db_session)

    response = await client.get(f"/admin/tools/{tool.id}/maintainers")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "maintainer-list" in response.text


@pytest.mark.integration
async def test_assign_maintainer_adds_user_and_returns_updated_list(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await _login_as_admin(client=client, db_session=db_session)
    contributor = await _create_contributor(db_session=db_session)
    tool = await _create_tool(db_session=db_session)

    response = await client.post(
        f"/admin/tools/{tool.id}/maintainers",
        data={"user_email": contributor.email},
    )

    assert response.status_code == 200
    assert "maintainer-list" in response.text
    assert contributor.email in response.text

    maintainer_repo = PostgreSQLToolMaintainerRepository(db_session)
    is_maintainer = await maintainer_repo.is_maintainer(tool_id=tool.id, user_id=contributor.id)
    assert is_maintainer is True


@pytest.mark.integration
async def test_assign_maintainer_rejects_nonexistent_email(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await _login_as_admin(client=client, db_session=db_session)
    tool = await _create_tool(db_session=db_session)

    response = await client.post(
        f"/admin/tools/{tool.id}/maintainers",
        data={"user_email": "nonexistent@example.com"},
    )

    assert response.status_code == 200
    assert "error" in response.text.lower() or "finns inte" in response.text.lower()


@pytest.mark.integration
async def test_remove_maintainer_removes_and_returns_updated_list(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await _login_as_admin(client=client, db_session=db_session)
    contributor = await _create_contributor(db_session=db_session)
    tool = await _create_tool(db_session=db_session)

    maintainer_model = ToolMaintainerModel(tool_id=tool.id, user_id=contributor.id)
    db_session.add(maintainer_model)
    await db_session.flush()

    maintainer_repo = PostgreSQLToolMaintainerRepository(db_session)
    is_before = await maintainer_repo.is_maintainer(tool_id=tool.id, user_id=contributor.id)
    assert is_before is True

    response = await client.delete(f"/admin/tools/{tool.id}/maintainers/{contributor.id}")

    assert response.status_code == 200
    assert "maintainer-list" in response.text
    assert contributor.email not in response.text

    is_after = await maintainer_repo.is_maintainer(tool_id=tool.id, user_id=contributor.id)
    assert is_after is False
