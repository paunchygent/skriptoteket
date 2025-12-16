"""Integration tests for user run history routes.

Tests /my-runs routes for users to view their past production runs.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.identity.models import AuthProvider, Role, Session, User
from skriptoteket.domain.scripting.models import (
    RunContext,
    RunStatus,
    VersionState,
    compute_content_hash,
)
from skriptoteket.infrastructure.db.models.tool import ToolModel
from skriptoteket.infrastructure.db.models.tool_run import ToolRunModel
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
) -> ToolModel:
    now = datetime.now(timezone.utc)
    tool = ToolModel(
        id=uuid.uuid4(),
        slug=slug,
        title=title,
        summary="Test tool summary",
        is_published=True,
        active_version_id=None,
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
) -> ToolVersionModel:
    now = datetime.now(timezone.utc)
    source_code = "def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>ok</p>'\n"
    entrypoint = "run_tool"
    model = ToolVersionModel(
        id=uuid.uuid4(),
        tool_id=tool_id,
        version_number=1,
        state=VersionState.ACTIVE,
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
        published_by_user_id=created_by_user_id,
        published_at=now,
        change_summary=None,
        review_note=None,
    )
    db_session.add(model)
    await db_session.flush()
    return model


async def _create_tool_run(
    *,
    db_session: AsyncSession,
    tool_id: uuid.UUID,
    version_id: uuid.UUID,
    requested_by_user_id: uuid.UUID,
    context: RunContext,
    status: RunStatus = RunStatus.SUCCEEDED,
    html_output: str | None = "<p>Result</p>",
) -> ToolRunModel:
    now = datetime.now(timezone.utc)
    model = ToolRunModel(
        id=uuid.uuid4(),
        tool_id=tool_id,
        version_id=version_id,
        requested_by_user_id=requested_by_user_id,
        context=context.value,
        status=status.value,
        started_at=now,
        finished_at=now,
        workdir_path="/tmp/run",
        input_filename="test.xlsx",
        input_size_bytes=1024,
        html_output=html_output,
        stdout="",
        stderr="",
        artifacts_manifest={"artifacts": []},
        error_summary=None,
    )
    db_session.add(model)
    await db_session.flush()
    return model


@pytest.mark.integration
async def test_view_run_renders_for_own_production_run(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /my-runs/{run_id} renders detail page for user's own PRODUCTION run."""
    user = await _login(
        client=client, db_session=db_session, role=Role.USER, email="user-run1@example.com"
    )
    tool = await _create_tool(db_session=db_session, slug="my-tool-1", title="My Tool")
    version = await _create_version(
        db_session=db_session, tool_id=tool.id, created_by_user_id=user.id
    )
    tool.active_version_id = version.id
    await db_session.flush()

    run = await _create_tool_run(
        db_session=db_session,
        tool_id=tool.id,
        version_id=version.id,
        requested_by_user_id=user.id,
        context=RunContext.PRODUCTION,
        html_output="<p>My result</p>",
    )

    response = await client.get(f"/my-runs/{run.id}")

    assert response.status_code == 200
    # Result partial should be rendered
    assert "huleedu-card" in response.text


@pytest.mark.integration
async def test_view_run_returns_404_for_other_users_run(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /my-runs/{run_id} returns 404 for another user's run."""
    await _login(
        client=client, db_session=db_session, role=Role.USER, email="user-run2@example.com"
    )
    other_user = await _create_user(
        db_session=db_session, role=Role.USER, email="other-user2@example.com"
    )
    tool = await _create_tool(db_session=db_session, slug="my-tool-2", title="My Tool")
    version = await _create_version(
        db_session=db_session, tool_id=tool.id, created_by_user_id=other_user.id
    )
    tool.active_version_id = version.id
    await db_session.flush()

    # Run belongs to other_user
    run = await _create_tool_run(
        db_session=db_session,
        tool_id=tool.id,
        version_id=version.id,
        requested_by_user_id=other_user.id,
        context=RunContext.PRODUCTION,
    )

    response = await client.get(f"/my-runs/{run.id}")

    assert response.status_code == 404


@pytest.mark.integration
async def test_view_run_returns_404_for_sandbox_run(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /my-runs/{run_id} returns 404 even for own SANDBOX run."""
    user = await _login(
        client=client, db_session=db_session, role=Role.USER, email="user-run3@example.com"
    )
    tool = await _create_tool(db_session=db_session, slug="my-tool-3", title="My Tool")
    version = await _create_version(
        db_session=db_session, tool_id=tool.id, created_by_user_id=user.id
    )
    tool.active_version_id = version.id
    await db_session.flush()

    # Sandbox run - should be hidden from my-runs
    run = await _create_tool_run(
        db_session=db_session,
        tool_id=tool.id,
        version_id=version.id,
        requested_by_user_id=user.id,
        context=RunContext.SANDBOX,
    )

    response = await client.get(f"/my-runs/{run.id}")

    assert response.status_code == 404


@pytest.mark.integration
async def test_view_run_requires_authentication(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /my-runs/{run_id} redirects to login when not authenticated."""
    user = await _create_user(db_session=db_session, role=Role.USER, email="user-run4@example.com")
    tool = await _create_tool(db_session=db_session, slug="my-tool-4", title="My Tool")
    version = await _create_version(
        db_session=db_session, tool_id=tool.id, created_by_user_id=user.id
    )
    tool.active_version_id = version.id
    await db_session.flush()

    run = await _create_tool_run(
        db_session=db_session,
        tool_id=tool.id,
        version_id=version.id,
        requested_by_user_id=user.id,
        context=RunContext.PRODUCTION,
    )

    # Clear any cookies to ensure not authenticated
    client.cookies.clear()

    response = await client.get(f"/my-runs/{run.id}", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


@pytest.mark.integration
async def test_view_run_returns_404_for_nonexistent_run(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /my-runs/{run_id} returns 404 for nonexistent run ID."""
    await _login(
        client=client, db_session=db_session, role=Role.USER, email="user-run5@example.com"
    )

    nonexistent_id = uuid.uuid4()
    response = await client.get(f"/my-runs/{nonexistent_id}")

    assert response.status_code == 404


@pytest.mark.integration
async def test_view_run_shows_error_for_failed_run(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /my-runs/{run_id} shows error summary for failed runs."""
    user = await _login(
        client=client, db_session=db_session, role=Role.USER, email="user-run6@example.com"
    )
    tool = await _create_tool(db_session=db_session, slug="my-tool-6", title="My Tool")
    version = await _create_version(
        db_session=db_session, tool_id=tool.id, created_by_user_id=user.id
    )
    tool.active_version_id = version.id
    await db_session.flush()

    run = await _create_tool_run(
        db_session=db_session,
        tool_id=tool.id,
        version_id=version.id,
        requested_by_user_id=user.id,
        context=RunContext.PRODUCTION,
        status=RunStatus.FAILED,
        html_output=None,
    )
    run.error_summary = "Script execution failed"
    await db_session.flush()

    response = await client.get(f"/my-runs/{run.id}")

    assert response.status_code == 200
    # Should show error styling (burgundy border)
    assert "border-color: var(--huleedu-burgundy)" in response.text
    assert "Ett fel uppstod" in response.text
