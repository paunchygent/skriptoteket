from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.catalog.models import Tool
from skriptoteket.domain.identity.models import AuthProvider, Role
from skriptoteket.domain.scripting.models import VersionState
from skriptoteket.infrastructure.db.models.category import CategoryModel
from skriptoteket.infrastructure.db.models.profession import ProfessionModel
from skriptoteket.infrastructure.db.models.profession_category import ProfessionCategoryModel

# Import ToolVersionModel to ensure foreign key resolution in metadata
from skriptoteket.infrastructure.db.models.tool_version import ToolVersionModel
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.repositories.category_repository import (
    PostgreSQLCategoryRepository,
)
from skriptoteket.infrastructure.repositories.profession_repository import (
    PostgreSQLProfessionRepository,
)
from skriptoteket.infrastructure.repositories.tool_repository import PostgreSQLToolRepository

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.mark.integration
async def test_profession_repository(db_session: AsyncSession) -> None:
    repo = PostgreSQLProfessionRepository(db_session)
    now = datetime.now(timezone.utc)

    prof_id = uuid.uuid4()
    # Manual insertion because repo is read-only
    model = ProfessionModel(
        id=prof_id,
        slug="engineer",
        label="Engineer",
        sort_order=1,
        created_at=now,
        updated_at=now,
    )
    db_session.add(model)
    await db_session.flush()

    # Test List
    all_profs = await repo.list_all()
    assert len(all_profs) >= 1
    # Check if our inserted profession is in the list
    assert any(p.id == prof_id for p in all_profs)
    assert all_profs[0].slug == "engineer" or any(p.slug == "engineer" for p in all_profs)

    # Test Get
    fetched = await repo.get_by_slug("engineer")
    assert fetched is not None
    assert fetched.label == "Engineer"

    by_ids = await repo.list_by_ids(profession_ids=[prof_id])
    assert [p.id for p in by_ids] == [prof_id]


@pytest.mark.integration
async def test_category_repository(db_session: AsyncSession) -> None:
    repo = PostgreSQLCategoryRepository(db_session)
    now = datetime.now(timezone.utc)

    cat_id = uuid.uuid4()
    model = CategoryModel(
        id=cat_id,
        slug="calculation",
        label="Calculation",
        created_at=now,
        updated_at=now,
    )
    db_session.add(model)
    await db_session.flush()

    all_cats = await repo.list_all()
    assert len(all_cats) >= 1
    assert any(c.id == cat_id for c in all_cats)

    by_ids = await repo.list_by_ids(category_ids=[cat_id])
    assert [c.id for c in by_ids] == [cat_id]


@pytest.mark.integration
async def test_category_repository_filters_by_profession_and_slug(db_session: AsyncSession) -> None:
    repo = PostgreSQLCategoryRepository(db_session)
    now = datetime.now(timezone.utc)

    prof_id = uuid.uuid4()
    prof = ProfessionModel(
        id=prof_id,
        slug="teacher",
        label="Teacher",
        sort_order=1,
        created_at=now,
        updated_at=now,
    )
    cat_id = uuid.uuid4()
    cat = CategoryModel(
        id=cat_id,
        slug="calculation",
        label="Calculation",
        created_at=now,
        updated_at=now,
    )
    db_session.add(prof)
    db_session.add(cat)
    db_session.add(ProfessionCategoryModel(profession_id=prof_id, category_id=cat_id, sort_order=1))
    await db_session.flush()

    fetched = await repo.get_by_slug("calculation")
    assert fetched is not None and fetched.id == cat_id

    by_profession = await repo.list_for_profession(profession_id=prof_id)
    assert [c.id for c in by_profession] == [cat_id]

    by_profession_slug = await repo.get_for_profession_by_slug(
        profession_id=prof_id,
        category_slug="calculation",
    )
    assert by_profession_slug is not None and by_profession_slug.id == cat_id


@pytest.mark.integration
async def test_tool_repository(db_session: AsyncSession) -> None:
    tool_repo = PostgreSQLToolRepository(db_session)
    now = datetime.now(timezone.utc)

    # Setup dependencies
    prof_id = uuid.uuid4()
    cat_id = uuid.uuid4()

    prof = ProfessionModel(
        id=prof_id, slug="p1", label="P1", sort_order=1, created_at=now, updated_at=now
    )
    cat = CategoryModel(id=cat_id, slug="c1", label="C1", created_at=now, updated_at=now)

    db_session.add(prof)
    db_session.add(cat)
    await db_session.flush()

    tool_id = uuid.uuid4()
    tool = Tool(
        id=tool_id,
        slug="my-tool",
        title="My Tool",
        summary="A summary",
        is_published=False,  # Draft
        active_version_id=None,
        created_at=now,
        updated_at=now,
    )

    await tool_repo.create_draft(tool=tool, profession_ids=[prof_id], category_ids=[cat_id])

    fetched = await tool_repo.get_by_id(tool_id=tool_id)
    assert fetched is not None
    assert fetched.title == "My Tool"

    by_slug = await tool_repo.get_by_slug(slug="my-tool")
    assert by_slug is not None
    assert by_slug.id == tool_id


@pytest.mark.integration
async def test_tool_repository_list_by_tags_and_updates(db_session: AsyncSession) -> None:
    tool_repo = PostgreSQLToolRepository(db_session)
    now = datetime.now(timezone.utc)

    user_id = uuid.uuid4()
    db_session.add(
        UserModel(
            id=user_id,
            email="tool-repo@example.com",
            password_hash="hash",
            role=Role.USER,
            auth_provider=AuthProvider.LOCAL,
            created_at=now,
            updated_at=now,
        )
    )

    prof_id = uuid.uuid4()
    cat_id = uuid.uuid4()
    db_session.add(
        ProfessionModel(
            id=prof_id,
            slug="p-tags",
            label="P",
            sort_order=1,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.add(
        CategoryModel(
            id=cat_id,
            slug="c-tags",
            label="C",
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()

    tool_a_id = uuid.uuid4()
    tool_b_id = uuid.uuid4()
    tool_c_id = uuid.uuid4()

    tool_a = Tool(
        id=tool_a_id,
        slug="a-tool",
        title="Alpha",
        summary=None,
        is_published=False,
        active_version_id=None,
        created_at=now,
        updated_at=now,
    )
    tool_b = Tool(
        id=tool_b_id,
        slug="b-tool",
        title="Beta",
        summary=None,
        is_published=False,
        active_version_id=None,
        created_at=now,
        updated_at=now,
    )
    tool_c = Tool(
        id=tool_c_id,
        slug="c-tool",
        title="Beta",
        summary=None,
        is_published=False,
        active_version_id=None,
        created_at=now,
        updated_at=now,
    )

    await tool_repo.create_draft(tool=tool_a, profession_ids=[prof_id], category_ids=[cat_id])
    await tool_repo.create_draft(tool=tool_b, profession_ids=[prof_id], category_ids=[cat_id])
    await tool_repo.create_draft(tool=tool_c, profession_ids=[prof_id], category_ids=[cat_id])

    await tool_repo.set_published(tool_id=tool_a_id, is_published=True, now=now)
    await tool_repo.set_published(tool_id=tool_b_id, is_published=True, now=now)
    # Keep tool_c unpublished

    published = await tool_repo.list_by_tags(profession_id=prof_id, category_id=cat_id)
    assert [t.id for t in published] == [tool_a_id, tool_b_id]

    updated = await tool_repo.update_metadata(
        tool_id=tool_a_id,
        title="Alpha (updated)",
        summary="Summary",
        now=now,
    )
    assert updated.title == "Alpha (updated)"
    assert updated.summary == "Summary"

    version_id = uuid.uuid4()
    db_session.add(
        ToolVersionModel(
            id=version_id,
            tool_id=tool_a_id,
            version_number=1,
            state=VersionState.DRAFT,
            source_code="print('hi')",
            entrypoint="run_tool",
            content_hash="hash",
            derived_from_version_id=None,
            created_by_user_id=user_id,
            created_at=now,
            submitted_for_review_by_user_id=None,
            submitted_for_review_at=None,
            reviewed_by_user_id=None,
            reviewed_at=None,
            published_by_user_id=None,
            published_at=None,
            change_summary=None,
            review_note=None,
        )
    )
    await db_session.flush()

    with_active = await tool_repo.set_active_version_id(
        tool_id=tool_a_id,
        active_version_id=version_id,
        now=now,
    )
    assert with_active.active_version_id == version_id


@pytest.mark.integration
async def test_tool_repository_list_tag_ids_and_replace_tags(db_session: AsyncSession) -> None:
    tool_repo = PostgreSQLToolRepository(db_session)
    now = datetime.now(timezone.utc)

    original_prof_id = uuid.uuid4()
    original_cat_id = uuid.uuid4()
    new_prof_id = uuid.uuid4()
    new_cat_id = uuid.uuid4()

    db_session.add(
        ProfessionModel(
            id=original_prof_id,
            slug="p-old",
            label="Old",
            sort_order=1,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.add(
        CategoryModel(
            id=original_cat_id,
            slug="c-old",
            label="Old",
            created_at=now,
            updated_at=now,
        )
    )
    db_session.add(
        ProfessionModel(
            id=new_prof_id,
            slug="p-new",
            label="New",
            sort_order=2,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.add(
        CategoryModel(
            id=new_cat_id,
            slug="c-new",
            label="New",
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()

    tool_id = uuid.uuid4()
    tool = Tool(
        id=tool_id,
        slug="tag-tool",
        title="Tag Tool",
        summary=None,
        is_published=False,
        active_version_id=None,
        created_at=now,
        updated_at=now,
    )
    await tool_repo.create_draft(
        tool=tool, profession_ids=[original_prof_id], category_ids=[original_cat_id]
    )

    profession_ids, category_ids = await tool_repo.list_tag_ids(tool_id=tool_id)
    assert set(profession_ids) == {original_prof_id}
    assert set(category_ids) == {original_cat_id}

    later = datetime.now(timezone.utc)
    await tool_repo.replace_tags(
        tool_id=tool_id,
        profession_ids=[new_prof_id],
        category_ids=[new_cat_id],
        now=later,
    )

    updated_prof_ids, updated_cat_ids = await tool_repo.list_tag_ids(tool_id=tool_id)
    assert set(updated_prof_ids) == {new_prof_id}
    assert set(updated_cat_ids) == {new_cat_id}

    refreshed = await tool_repo.get_by_id(tool_id=tool_id)
    assert refreshed is not None
    assert refreshed.updated_at >= later
