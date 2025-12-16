from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.identity.models import AuthProvider, Role, Session, User
from skriptoteket.domain.scripting.models import VersionState, compute_content_hash
from skriptoteket.infrastructure.db.models.category import CategoryModel
from skriptoteket.infrastructure.db.models.profession import ProfessionModel
from skriptoteket.infrastructure.db.models.profession_category import ProfessionCategoryModel
from skriptoteket.infrastructure.db.models.tool import ToolModel
from skriptoteket.infrastructure.db.models.tool_category import ToolCategoryModel
from skriptoteket.infrastructure.db.models.tool_profession import ToolProfessionModel
from skriptoteket.infrastructure.db.models.tool_version import ToolVersionModel
from skriptoteket.infrastructure.repositories.session_repository import PostgreSQLSessionRepository
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


async def _create_profession_and_category(
    *, db_session: AsyncSession, profession_slug: str, category_slug: str
) -> tuple[ProfessionModel, CategoryModel]:
    now = datetime.now(timezone.utc)
    profession = ProfessionModel(
        id=uuid.uuid4(),
        slug=profession_slug,
        label="Lärare",
        sort_order=1,
        created_at=now,
        updated_at=now,
    )
    category = CategoryModel(
        id=uuid.uuid4(),
        slug=category_slug,
        label="Administration",
        created_at=now,
        updated_at=now,
    )
    db_session.add(profession)
    db_session.add(category)
    db_session.add(
        ProfessionCategoryModel(
            profession_id=profession.id,
            category_id=category.id,
            sort_order=1,
        )
    )
    await db_session.flush()
    return profession, category


async def _create_tool_with_tags(
    *,
    db_session: AsyncSession,
    profession_id: uuid.UUID,
    category_id: uuid.UUID,
    title: str,
    summary: str | None,
) -> ToolModel:
    now = datetime.now(timezone.utc)
    tool = ToolModel(
        id=uuid.uuid4(),
        slug=f"test-tool-{uuid.uuid4().hex[:8]}",
        title=title,
        summary=summary,
        is_published=False,
        active_version_id=None,
        created_at=now,
        updated_at=now,
    )
    db_session.add(tool)
    db_session.add(ToolProfessionModel(tool_id=tool.id, profession_id=profession_id))
    db_session.add(ToolCategoryModel(tool_id=tool.id, category_id=category_id))
    await db_session.flush()
    return tool


async def _create_in_review_version(
    *,
    db_session: AsyncSession,
    tool_id: uuid.UUID,
    created_by_user_id: uuid.UUID,
    version_number: int,
    source_code: str,
) -> ToolVersionModel:
    now = datetime.now(timezone.utc)
    entrypoint = "run_tool"
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
async def test_admin_can_update_tool_metadata_without_publish_overwriting_catalog_summary(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await _login_as_admin(client=client, db_session=db_session)
    author = await _create_author(db_session=db_session)

    suffix = uuid.uuid4().hex[:8]
    profession_slug = f"teacher-{suffix}"
    category_slug = f"administration-{suffix}"
    profession, category = await _create_profession_and_category(
        db_session=db_session,
        profession_slug=profession_slug,
        category_slug=category_slug,
    )

    original_summary_marker = "ORIGINAL_COLAB_SNIPPET"
    tool = await _create_tool_with_tags(
        db_session=db_session,
        profession_id=profession.id,
        category_id=category.id,
        title="Gammal titel",
        summary=f"{original_summary_marker}\nprint('hello')",
    )

    reviewed_v1 = await _create_in_review_version(
        db_session=db_session,
        tool_id=tool.id,
        created_by_user_id=author.id,
        version_number=1,
        source_code=(
            "def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>v1</p>'\n"
        ),
    )

    publish_v1 = await client.post(
        f"/admin/tool-versions/{reviewed_v1.id}/publish",
        data={"change_summary": "Publish v1"},
        follow_redirects=False,
    )
    assert publish_v1.status_code == 303

    publish_tool = await client.post(
        f"/admin/tools/{tool.id}/publish",
        follow_redirects=False,
    )
    assert publish_tool.status_code == 303

    # Katalog shows tool.summary (not script source).
    browse_before = await client.get(f"/browse/{profession_slug}/{category_slug}")
    assert browse_before.status_code == 200
    assert "Gammal titel" in browse_before.text
    assert original_summary_marker in browse_before.text

    update_meta = await client.post(
        f"/admin/tools/{tool.id}/metadata",
        data={"title": "Ny titel", "summary": "Ny sammanfattning"},
        follow_redirects=False,
    )
    assert update_meta.status_code == 303

    browse_after = await client.get(f"/browse/{profession_slug}/{category_slug}")
    assert browse_after.status_code == 200
    assert "Ny titel" in browse_after.text
    assert "Ny sammanfattning" in browse_after.text
    assert original_summary_marker not in browse_after.text

    # Publish a new script version and ensure catalog metadata remains unchanged.
    reviewed_v3 = await _create_in_review_version(
        db_session=db_session,
        tool_id=tool.id,
        created_by_user_id=author.id,
        version_number=3,
        source_code=(
            "def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>v2</p>'\n"
        ),
    )
    publish_v3 = await client.post(
        f"/admin/tool-versions/{reviewed_v3.id}/publish",
        data={"change_summary": "Publish v2"},
        follow_redirects=False,
    )
    assert publish_v3.status_code == 303

    browse_after_second_publish = await client.get(f"/browse/{profession_slug}/{category_slug}")
    assert browse_after_second_publish.status_code == 200
    assert "Ny titel" in browse_after_second_publish.text
    assert "Ny sammanfattning" in browse_after_second_publish.text
    assert original_summary_marker not in browse_after_second_publish.text
