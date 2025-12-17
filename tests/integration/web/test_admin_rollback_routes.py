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
from skriptoteket.infrastructure.repositories.tool_version_repository import (
    PostgreSQLToolVersionRepository,
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


async def _login_as_superuser(*, client: AsyncClient, db_session: AsyncSession) -> User:
    user_repo = PostgreSQLUserRepository(db_session)
    session_repo = PostgreSQLSessionRepository(db_session)

    now = datetime.now(timezone.utc)
    superuser = User(
        id=uuid.uuid4(),
        email="superuser@example.com",
        role=Role.SUPERUSER,
        auth_provider=AuthProvider.LOCAL,
        created_at=now,
        updated_at=now,
    )
    await user_repo.create(user=superuser, password_hash="hash")

    session_id = uuid.uuid4()
    session = Session(
        id=session_id,
        user_id=superuser.id,
        csrf_token="csrf",
        created_at=now,
        expires_at=now + timedelta(days=1),
    )
    await session_repo.create(session=session)
    await db_session.flush()

    client.cookies.set("skriptoteket_session", str(session_id))
    return superuser


async def _create_tool_with_versions(
    *,
    db_session: AsyncSession,
    created_by_user_id: uuid.UUID,
) -> tuple[ToolModel, ToolVersionModel, ToolVersionModel]:
    """Create tool with an ACTIVE version and an ARCHIVED version."""
    now = datetime.now(timezone.utc)
    tool = ToolModel(
        id=uuid.uuid4(),
        slug="rollback-test-tool",
        title="Rollback Test Tool",
        summary="Summary",
        is_published=True,
        active_version_id=None,
        created_at=now,
        updated_at=now,
    )
    db_session.add(tool)
    await db_session.flush()

    source_code = "def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>ok</p>'\n"
    entrypoint = "run_tool"
    content_hash = compute_content_hash(entrypoint=entrypoint, source_code=source_code)

    # Archived version (the one we want to rollback to)
    archived_version = ToolVersionModel(
        id=uuid.uuid4(),
        tool_id=tool.id,
        version_number=1,
        state=VersionState.ARCHIVED,
        source_code=source_code,
        entrypoint=entrypoint,
        content_hash=content_hash,
        derived_from_version_id=None,
        created_by_user_id=created_by_user_id,
        created_at=now,
        submitted_for_review_by_user_id=None,
        submitted_for_review_at=None,
        reviewed_by_user_id=None,
        reviewed_at=None,
        published_by_user_id=created_by_user_id,
        published_at=now,
        change_summary="Original version",
        review_note=None,
    )
    db_session.add(archived_version)

    # Active version
    active_version = ToolVersionModel(
        id=uuid.uuid4(),
        tool_id=tool.id,
        version_number=2,
        state=VersionState.ACTIVE,
        source_code=source_code,
        entrypoint=entrypoint,
        content_hash=content_hash,
        derived_from_version_id=archived_version.id,
        created_by_user_id=created_by_user_id,
        created_at=now,
        submitted_for_review_by_user_id=None,
        submitted_for_review_at=None,
        reviewed_by_user_id=None,
        reviewed_at=None,
        published_by_user_id=created_by_user_id,
        published_at=now,
        change_summary="Current version",
        review_note=None,
    )
    db_session.add(active_version)
    await db_session.flush()

    # Update tool pointer
    tool.active_version_id = active_version.id
    await db_session.flush()

    return tool, archived_version, active_version


@pytest.mark.integration
async def test_rollback_requires_superuser(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Admin should not be able to rollback - 403 expected."""
    admin = await _login_as_admin(client=client, db_session=db_session)
    tool, archived_version, _ = await _create_tool_with_versions(
        db_session=db_session, created_by_user_id=admin.id
    )

    response = await client.post(
        f"/admin/tool-versions/{archived_version.id}/rollback",
        follow_redirects=False,
    )

    assert response.status_code == 403


@pytest.mark.integration
async def test_rollback_creates_new_active_version(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    superuser = await _login_as_superuser(client=client, db_session=db_session)
    tool, archived_version, previous_active = await _create_tool_with_versions(
        db_session=db_session, created_by_user_id=superuser.id
    )

    response = await client.post(
        f"/admin/tool-versions/{archived_version.id}/rollback",
        follow_redirects=False,
    )

    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith("/admin/tool-versions/")
    new_version_id = uuid.UUID(location.rsplit("/", 1)[-1])
    assert new_version_id != archived_version.id
    assert new_version_id != previous_active.id

    versions_repo = PostgreSQLToolVersionRepository(db_session)
    new_version = await versions_repo.get_by_id(version_id=new_version_id)
    assert new_version is not None
    assert new_version.state is VersionState.ACTIVE
    assert new_version.version_number == 3
    assert new_version.derived_from_version_id == archived_version.id


@pytest.mark.integration
async def test_rollback_archives_previous_active(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    superuser = await _login_as_superuser(client=client, db_session=db_session)
    tool, archived_version, previous_active = await _create_tool_with_versions(
        db_session=db_session, created_by_user_id=superuser.id
    )

    response = await client.post(
        f"/admin/tool-versions/{archived_version.id}/rollback",
        follow_redirects=False,
    )

    assert response.status_code == 303

    versions_repo = PostgreSQLToolVersionRepository(db_session)
    updated_previous = await versions_repo.get_by_id(version_id=previous_active.id)
    assert updated_previous is not None
    assert updated_previous.state is VersionState.ARCHIVED
