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


async def _create_tool(*, db_session: AsyncSession, slug: str, title: str) -> ToolModel:
    now = datetime.now(timezone.utc)
    tool = ToolModel(
        id=uuid.uuid4(),
        slug=slug,
        title=title,
        summary="Summary",
        is_published=False,
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
    version_number: int,
    state: VersionState,
    source_code: str,
    derived_from_version_id: uuid.UUID | None = None,
) -> ToolVersionModel:
    now = datetime.now(timezone.utc)
    entrypoint = "run_tool"
    model = ToolVersionModel(
        id=uuid.uuid4(),
        tool_id=tool_id,
        version_number=version_number,
        state=state,
        source_code=source_code,
        entrypoint=entrypoint,
        content_hash=compute_content_hash(entrypoint=entrypoint, source_code=source_code),
        derived_from_version_id=derived_from_version_id,
        created_by_user_id=created_by_user_id,
        created_at=now,
        submitted_for_review_by_user_id=created_by_user_id
        if state is VersionState.IN_REVIEW
        else None,
        submitted_for_review_at=now if state is VersionState.IN_REVIEW else None,
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
async def test_admin_editor_for_tool_renders_starter_template_when_no_versions(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await _login(client=client, db_session=db_session, role=Role.ADMIN, email="admin@example.com")
    tool = await _create_tool(db_session=db_session, slug="tool-no-versions", title="No Versions")

    response = await client.get(f"/admin/tools/{tool.id}")

    assert response.status_code == 200
    assert "Skripteditorn" in response.text
    assert "No Versions" in response.text
    assert "Received file of" in response.text


@pytest.mark.integration
async def test_contributor_editor_for_tool_renders_starter_template_when_no_versions(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await _login(
        client=client, db_session=db_session, role=Role.CONTRIBUTOR, email="contrib@example.com"
    )
    tool = await _create_tool(
        db_session=db_session, slug="tool-no-versions-contrib", title="No Versions"
    )

    response = await client.get(f"/admin/tools/{tool.id}")

    assert response.status_code == 200
    assert "Skripteditorn" in response.text
    assert "Received file of" in response.text


@pytest.mark.integration
async def test_contributor_editor_for_tool_renders_own_draft_version(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    contributor = await _login(
        client=client, db_session=db_session, role=Role.CONTRIBUTOR, email="contrib2@example.com"
    )
    tool = await _create_tool(db_session=db_session, slug="tool-with-draft", title="With Draft")

    marker = "# DRAFT_MARKER"
    draft = await _create_version(
        db_session=db_session,
        tool_id=tool.id,
        created_by_user_id=contributor.id,
        version_number=1,
        state=VersionState.DRAFT,
        source_code=f"def run_tool(input_path: str, output_dir: str) -> str:\n    {marker}\n    return '<p>ok</p>'\n",
    )
    del draft

    response = await client.get(f"/admin/tools/{tool.id}")

    assert response.status_code == 200
    assert marker in response.text


@pytest.mark.integration
async def test_contributor_editor_for_tool_renders_active_version_derived_from_their_work(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    contributor = await _login(
        client=client,
        db_session=db_session,
        role=Role.CONTRIBUTOR,
        email="contrib-active@example.com",
    )
    admin = await _create_user(
        db_session=db_session,
        role=Role.ADMIN,
        email="admin-active@example.com",
    )
    tool = await _create_tool(db_session=db_session, slug="tool-with-active", title="With Active")

    author_version = await _create_version(
        db_session=db_session,
        tool_id=tool.id,
        created_by_user_id=contributor.id,
        version_number=1,
        state=VersionState.ARCHIVED,
        source_code="def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>v1</p>'\n",
    )

    marker = "# ACTIVE_MARKER"
    active = await _create_version(
        db_session=db_session,
        tool_id=tool.id,
        created_by_user_id=admin.id,
        version_number=2,
        state=VersionState.ACTIVE,
        derived_from_version_id=author_version.id,
        source_code=f"def run_tool(input_path: str, output_dir: str) -> str:\n    {marker}\n    return '<p>v2</p>'\n",
    )

    tool.active_version_id = active.id
    tool.is_published = True
    await db_session.flush()

    response = await client.get(f"/admin/tools/{tool.id}")

    assert response.status_code == 200
    assert marker in response.text


@pytest.mark.integration
async def test_version_history_hides_versions_from_other_contributors(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    contributor_a = await _login(
        client=client, db_session=db_session, role=Role.CONTRIBUTOR, email="contrib-a@example.com"
    )
    contributor_b = await _create_user(
        db_session=db_session, role=Role.CONTRIBUTOR, email="contrib-b@example.com"
    )
    tool = await _create_tool(db_session=db_session, slug="tool-history", title="History")

    visible = await _create_version(
        db_session=db_session,
        tool_id=tool.id,
        created_by_user_id=contributor_a.id,
        version_number=1,
        state=VersionState.DRAFT,
        source_code="def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>a</p>'\n",
    )
    hidden = await _create_version(
        db_session=db_session,
        tool_id=tool.id,
        created_by_user_id=contributor_b.id,
        version_number=2,
        state=VersionState.DRAFT,
        source_code="def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>b</p>'\n",
    )

    response = await client.get(f"/admin/tools/{tool.id}/versions")

    assert response.status_code == 200
    assert str(visible.id) in response.text
    assert str(hidden.id) not in response.text


@pytest.mark.integration
async def test_editor_for_version_is_forbidden_when_version_not_owned(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await _login(
        client=client,
        db_session=db_session,
        role=Role.CONTRIBUTOR,
        email="contrib-owner-a@example.com",
    )
    contributor_b = await _create_user(
        db_session=db_session, role=Role.CONTRIBUTOR, email="contrib-owner-b@example.com"
    )
    tool = await _create_tool(db_session=db_session, slug="tool-ownership", title="Ownership")
    version = await _create_version(
        db_session=db_session,
        tool_id=tool.id,
        created_by_user_id=contributor_b.id,
        version_number=1,
        state=VersionState.DRAFT,
        source_code="def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>b</p>'\n",
    )

    response = await client.get(f"/admin/tool-versions/{version.id}")

    assert response.status_code == 403
    assert "Du saknar behörighet" in response.text


@pytest.mark.integration
async def test_create_draft_version_redirects_to_new_version(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await _login(
        client=client,
        db_session=db_session,
        role=Role.CONTRIBUTOR,
        email="contrib-create@example.com",
    )
    tool = await _create_tool(db_session=db_session, slug="tool-create", title="Create")

    marker = "# CREATED_MARKER"
    response = await client.post(
        f"/admin/tools/{tool.id}/versions",
        data={
            "entrypoint": "run_tool",
            "source_code": f"def run_tool(input_path: str, output_dir: str) -> str:\n    {marker}\n    return '<p>ok</p>'\n",
            "change_summary": "Initial",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/admin/tool-versions/")


@pytest.mark.integration
async def test_create_draft_version_renders_validation_error_for_invalid_derived_from_uuid(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    contributor = await _login(
        client=client,
        db_session=db_session,
        role=Role.CONTRIBUTOR,
        email="contrib-create-error@example.com",
    )
    tool = await _create_tool(db_session=db_session, slug="tool-create-error", title="Create Error")
    await _create_version(
        db_session=db_session,
        tool_id=tool.id,
        created_by_user_id=contributor.id,
        version_number=1,
        state=VersionState.DRAFT,
        source_code="def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>ok</p>'\n",
    )

    response = await client.post(
        f"/admin/tools/{tool.id}/versions",
        data={
            "entrypoint": "run_tool",
            "source_code": "def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>ok</p>'\n",
            "derived_from_version_id": "not-a-uuid",
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert "Ogiltig indata" in response.text


@pytest.mark.integration
async def test_save_draft_creates_new_snapshot_and_redirects(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    contributor = await _login(
        client=client,
        db_session=db_session,
        role=Role.CONTRIBUTOR,
        email="contrib-save@example.com",
    )
    tool = await _create_tool(db_session=db_session, slug="tool-save", title="Save")
    draft = await _create_version(
        db_session=db_session,
        tool_id=tool.id,
        created_by_user_id=contributor.id,
        version_number=1,
        state=VersionState.DRAFT,
        source_code="def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>v1</p>'\n",
    )

    response = await client.post(
        f"/admin/tool-versions/{draft.id}/save",
        data={
            "entrypoint": "run_tool",
            "source_code": "def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>v2</p>'\n",
            "expected_parent_version_id": str(draft.id),
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/admin/tool-versions/")
    assert response.headers["location"] != f"/admin/tool-versions/{draft.id}"


@pytest.mark.integration
async def test_save_draft_renders_error_for_invalid_expected_parent_uuid(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    contributor = await _login(
        client=client,
        db_session=db_session,
        role=Role.CONTRIBUTOR,
        email="contrib-save-error@example.com",
    )
    tool = await _create_tool(db_session=db_session, slug="tool-save-error", title="Save Error")
    draft = await _create_version(
        db_session=db_session,
        tool_id=tool.id,
        created_by_user_id=contributor.id,
        version_number=1,
        state=VersionState.DRAFT,
        source_code="def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>v1</p>'\n",
    )

    response = await client.post(
        f"/admin/tool-versions/{draft.id}/save",
        data={
            "entrypoint": "run_tool",
            "source_code": "def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>v2</p>'\n",
            "expected_parent_version_id": "not-a-uuid",
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert "Versionen stämmer inte längre" in response.text


@pytest.mark.integration
async def test_submit_review_conflict_renders_editor_error(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    contributor = await _login(
        client=client,
        db_session=db_session,
        role=Role.CONTRIBUTOR,
        email="contrib-review@example.com",
    )
    tool = await _create_tool(db_session=db_session, slug="tool-review", title="Review")
    in_review = await _create_version(
        db_session=db_session,
        tool_id=tool.id,
        created_by_user_id=contributor.id,
        version_number=1,
        state=VersionState.IN_REVIEW,
        source_code="def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>v1</p>'\n",
    )

    response = await client.post(
        f"/admin/tool-versions/{in_review.id}/submit-review",
        data={"review_note": "Please review"},
        follow_redirects=False,
    )

    assert response.status_code == 409
    assert "konflikt" in response.text.lower()
