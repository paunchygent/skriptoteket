from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.catalog.models import Tool
from skriptoteket.infrastructure.db.models.category import CategoryModel
from skriptoteket.infrastructure.db.models.profession import ProfessionModel

# Import ToolVersionModel to ensure foreign key resolution in metadata
from skriptoteket.infrastructure.db.models.tool_version import ToolVersionModel  # noqa: F401
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
