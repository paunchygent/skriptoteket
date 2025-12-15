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
from skriptoteket.infrastructure.repositories.tool_repository import PostgreSQLToolRepository
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


async def _create_author(*, db_session: AsyncSession) -> User:
    now = datetime.now(timezone.utc)
    author = User(
        id=uuid.uuid4(),
        email="author@example.com",
        role=Role.CONTRIBUTOR,
        auth_provider=AuthProvider.LOCAL,
        created_at=now,
        updated_at=now,
    )
    await PostgreSQLUserRepository(db_session).create(user=author, password_hash="hash")
    await db_session.flush()
    return author


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


async def _create_in_review_version(
    *,
    db_session: AsyncSession,
    tool_id: uuid.UUID,
    created_by_user_id: uuid.UUID,
    version_number: int = 1,
) -> ToolVersionModel:
    now = datetime.now(timezone.utc)
    entrypoint = "run_tool"
    source_code = (
        "def run_tool(input_path: str, output_dir: str) -> str:\n"
        "    return '<p>ok</p>'\n"
    )
    model = ToolVersionModel(
        id=uuid.uuid4(),
        tool_id=tool_id,
        version_number=version_number,
        state=VersionState.IN_REVIEW,
        source_code=source_code,
        entrypoint=entrypoint,
        content_hash=compute_content_hash(entrypoint=entrypoint, source_code=source_code),
        derived_from_version_id=None,
        created_by_user_id=created_by_user_id,
        created_at=now,
        submitted_for_review_by_user_id=created_by_user_id,
        submitted_for_review_at=now,
        reviewed_by_user_id=None,
        reviewed_at=None,
        published_by_user_id=None,
        published_at=None,
        change_summary=None,
        review_note=None,
    )
    db_session.add(model)
    await db_session.flush()
    return model


@pytest.mark.integration
async def test_publish_version_route_publishes_in_review_and_updates_tool_pointer(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    admin = await _login_as_admin(client=client, db_session=db_session)
    author = await _create_author(db_session=db_session)
    tool = await _create_tool(db_session=db_session)
    reviewed = await _create_in_review_version(
        db_session=db_session,
        tool_id=tool.id,
        created_by_user_id=author.id,
        version_number=1,
    )
    await db_session.flush()

    response = await client.post(
        f"/admin/tool-versions/{reviewed.id}/publish",
        data={"change_summary": "Publish v1"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith("/admin/tool-versions/")
    new_version_id = uuid.UUID(location.rsplit("/", 1)[-1])
    assert new_version_id != reviewed.id

    versions_repo = PostgreSQLToolVersionRepository(db_session)
    published = await versions_repo.get_by_id(version_id=new_version_id)
    assert published is not None
    assert published.state is VersionState.ACTIVE
    assert published.derived_from_version_id == reviewed.id

    archived_reviewed = await versions_repo.get_by_id(version_id=reviewed.id)
    assert archived_reviewed is not None
    assert archived_reviewed.state is VersionState.ARCHIVED
    assert archived_reviewed.published_by_user_id == admin.id
    assert archived_reviewed.published_at is not None

    tool_repo = PostgreSQLToolRepository(db_session)
    updated_tool = await tool_repo.get_by_id(tool_id=tool.id)
    assert updated_tool is not None
    assert updated_tool.active_version_id == new_version_id


@pytest.mark.integration
async def test_request_changes_route_archives_in_review_and_creates_new_draft(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    admin = await _login_as_admin(client=client, db_session=db_session)
    author = await _create_author(db_session=db_session)
    tool = await _create_tool(db_session=db_session)
    reviewed = await _create_in_review_version(
        db_session=db_session,
        tool_id=tool.id,
        created_by_user_id=author.id,
        version_number=1,
    )
    await db_session.flush()

    response = await client.post(
        f"/admin/tool-versions/{reviewed.id}/request-changes",
        data={"message": "  Please fix  "},
        follow_redirects=False,
    )

    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith("/admin/tool-versions/")
    new_version_id = uuid.UUID(location.rsplit("/", 1)[-1])
    assert new_version_id != reviewed.id

    versions_repo = PostgreSQLToolVersionRepository(db_session)
    new_draft = await versions_repo.get_by_id(version_id=new_version_id)
    assert new_draft is not None
    assert new_draft.state is VersionState.DRAFT
    assert new_draft.derived_from_version_id == reviewed.id
    assert new_draft.created_by_user_id == author.id
    assert new_draft.change_summary == "Please fix"

    archived_reviewed = await versions_repo.get_by_id(version_id=reviewed.id)
    assert archived_reviewed is not None
    assert archived_reviewed.state is VersionState.ARCHIVED
    assert archived_reviewed.reviewed_by_user_id == admin.id
    assert archived_reviewed.reviewed_at is not None
