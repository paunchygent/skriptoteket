"""Integration tests for user-facing tool execution routes.

Tests /tools/{slug}/run routes for authenticated users to run published tools.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.identity.models import AuthProvider, Role, Session, User
from skriptoteket.domain.scripting.models import VersionState, compute_content_hash
from skriptoteket.infrastructure.db.models.tool import ToolModel
from skriptoteket.infrastructure.db.models.tool_version import ToolVersionModel
from skriptoteket.infrastructure.repositories.session_repository import PostgreSQLSessionRepository
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository

pytestmark = pytest.mark.asyncio(loop_scope="module")


async def _create_user(
    *,
    db_session: AsyncSession,
    role: Role,
    email: str,
) -> User:
    user_repo = PostgreSQLUserRepository(db_session)

    now = datetime.now(timezone.utc)
    user = User(
        id=uuid.uuid4(),
        email=email,
        role=role,
        auth_provider=AuthProvider.LOCAL,
        created_at=now,
        updated_at=now,
    )
    await user_repo.create(user=user, password_hash="hash")
    await db_session.flush()
    return user


async def _login(
    *,
    client: AsyncClient,
    db_session: AsyncSession,
    role: Role,
    email: str,
) -> User:
    session_repo = PostgreSQLSessionRepository(db_session)

    user = await _create_user(db_session=db_session, role=role, email=email)

    now = datetime.now(timezone.utc)
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


async def _create_tool(
    *,
    db_session: AsyncSession,
    slug: str,
    title: str,
    is_published: bool = False,
    active_version_id: uuid.UUID | None = None,
) -> ToolModel:
    now = datetime.now(timezone.utc)
    tool = ToolModel(
        id=uuid.uuid4(),
        slug=slug,
        title=title,
        summary="Test tool summary",
        is_published=is_published,
        active_version_id=active_version_id,
        created_at=now,
        updated_at=now,
    )
    db_session.add(tool)
    await db_session.flush()
    return tool


async def _create_version(
    *,
    db_session: AsyncSession,
    tool_id: uuid.UUID,
    created_by_user_id: uuid.UUID,
    version_number: int,
    state: VersionState,
) -> ToolVersionModel:
    now = datetime.now(timezone.utc)
    source_code = "def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>ok</p>'\n"
    entrypoint = "run_tool"
    model = ToolVersionModel(
        id=uuid.uuid4(),
        tool_id=tool_id,
        version_number=version_number,
        state=state,
        source_code=source_code,
        entrypoint=entrypoint,
        content_hash=compute_content_hash(entrypoint=entrypoint, source_code=source_code),
        derived_from_version_id=None,
        created_by_user_id=created_by_user_id,
        created_at=now,
        submitted_for_review_by_user_id=None,
        submitted_for_review_at=None,
        reviewed_by_user_id=None,
        reviewed_at=None,
        published_by_user_id=created_by_user_id if state is VersionState.ACTIVE else None,
        published_at=now if state is VersionState.ACTIVE else None,
        change_summary=None,
        review_note=None,
    )
    db_session.add(model)
    await db_session.flush()
    return model


@pytest.mark.integration
async def test_show_run_form_renders_for_published_tool(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /tools/{slug}/run renders form when tool is published with active version."""
    admin = await _login(
        client=client, db_session=db_session, role=Role.ADMIN, email="admin-run1@example.com"
    )
    tool = await _create_tool(db_session=db_session, slug="runnable-tool-1", title="Runnable Tool")
    version = await _create_version(
        db_session=db_session,
        tool_id=tool.id,
        created_by_user_id=admin.id,
        version_number=1,
        state=VersionState.ACTIVE,
    )

    # Update tool to published with active version
    tool.is_published = True
    tool.active_version_id = version.id
    await db_session.flush()

    response = await client.get(f"/tools/{tool.slug}/run")

    assert response.status_code == 200
    assert "Runnable Tool" in response.text
    assert "Ladda upp fil" in response.text
    assert "Kör" in response.text


@pytest.mark.integration
async def test_show_run_form_returns_404_for_unpublished_tool(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /tools/{slug}/run returns 404 when tool is not published."""
    admin = await _login(
        client=client, db_session=db_session, role=Role.ADMIN, email="admin-run2@example.com"
    )
    tool = await _create_tool(
        db_session=db_session,
        slug="unpublished-tool-1",
        title="Unpublished Tool",
        is_published=False,
    )
    version = await _create_version(
        db_session=db_session,
        tool_id=tool.id,
        created_by_user_id=admin.id,
        version_number=1,
        state=VersionState.ACTIVE,
    )
    tool.active_version_id = version.id
    await db_session.flush()

    response = await client.get(f"/tools/{tool.slug}/run")

    assert response.status_code == 404


@pytest.mark.integration
async def test_show_run_form_returns_404_for_tool_without_active_version(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /tools/{slug}/run returns 404 when tool has no active version."""
    await _login(
        client=client, db_session=db_session, role=Role.ADMIN, email="admin-run3@example.com"
    )
    tool = await _create_tool(
        db_session=db_session,
        slug="no-active-version-1",
        title="No Active Version",
        is_published=True,
        active_version_id=None,
    )
    await db_session.flush()

    response = await client.get(f"/tools/{tool.slug}/run")

    assert response.status_code == 404


@pytest.mark.integration
async def test_show_run_form_requires_authentication(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /tools/{slug}/run redirects to login when not authenticated."""
    admin = await _create_user(
        db_session=db_session, role=Role.ADMIN, email="admin-run4@example.com"
    )
    tool = await _create_tool(db_session=db_session, slug="auth-required-1", title="Auth Required")
    version = await _create_version(
        db_session=db_session,
        tool_id=tool.id,
        created_by_user_id=admin.id,
        version_number=1,
        state=VersionState.ACTIVE,
    )
    tool.is_published = True
    tool.active_version_id = version.id
    await db_session.flush()

    # Clear any cookies to ensure not authenticated
    client.cookies.clear()

    response = await client.get(f"/tools/{tool.slug}/run", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


@pytest.mark.integration
async def test_show_run_form_returns_404_for_nonexistent_tool(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /tools/{slug}/run returns 404 for nonexistent tool slug."""
    await _login(
        client=client, db_session=db_session, role=Role.USER, email="user-run5@example.com"
    )

    response = await client.get("/tools/nonexistent-tool-slug/run")

    assert response.status_code == 404


@pytest.mark.integration
async def test_show_run_form_accessible_to_regular_user(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /tools/{slug}/run is accessible to regular users for published tools."""
    admin = await _create_user(
        db_session=db_session, role=Role.ADMIN, email="admin-run6@example.com"
    )
    await _login(
        client=client, db_session=db_session, role=Role.USER, email="user-run6@example.com"
    )
    tool = await _create_tool(db_session=db_session, slug="user-runnable-1", title="User Runnable")
    version = await _create_version(
        db_session=db_session,
        tool_id=tool.id,
        created_by_user_id=admin.id,
        version_number=1,
        state=VersionState.ACTIVE,
    )
    tool.is_published = True
    tool.active_version_id = version.id
    await db_session.flush()

    response = await client.get(f"/tools/{tool.slug}/run")

    assert response.status_code == 200
    assert "User Runnable" in response.text
