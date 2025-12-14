from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.catalog.models import Tool
from skriptoteket.domain.scripting.models import ToolVersion, VersionState
from skriptoteket.infrastructure.repositories.tool_version_repository import (
    PostgreSQLToolVersionRepository,
)

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.fixture
def now():
    return datetime.now(timezone.utc)


@pytest.fixture
async def tool(db_session: AsyncSession, now: datetime) -> Tool:
    tool_id = uuid4()
    tool = Tool(
        id=tool_id,
        slug="test-tool",
        title="Test Tool",
        summary="Summary",
        created_at=now,
        updated_at=now,
    )
    # Use ToolModel directly to avoid profession/category setup overhead
    from skriptoteket.infrastructure.db.models.tool import ToolModel

    model = ToolModel(
        id=tool_id,
        slug="test-tool",
        title="Test Tool",
        summary="Summary",
        created_at=now,
        updated_at=now,
    )
    db_session.add(model)
    await db_session.flush()
    return tool


@pytest.mark.integration
async def test_tool_version_crud(db_session: AsyncSession, tool: Tool, now: datetime) -> None:
    repo = PostgreSQLToolVersionRepository(db_session)

    version_id = uuid4()
    user_id = uuid4()  # We don't verify user FK in DB usually? Or we do?
    # If user FK exists, we must create user.
    # Let's create a user.
    from skriptoteket.domain.identity.models import AuthProvider, Role
    from skriptoteket.infrastructure.db.models.user import UserModel

    user_model = UserModel(
        id=user_id,
        email="test@test.com",
        password_hash="hash",
        role=Role.USER,
        auth_provider=AuthProvider.LOCAL,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user_model)
    await db_session.flush()

    # Create
    version = ToolVersion(
        id=version_id,
        tool_id=tool.id,
        version_number=1,
        state=VersionState.DRAFT,
        source_code="print('hi')",
        entrypoint="main.py",
        content_hash="hash",
        created_by_user_id=user_id,
        created_at=now,
    )
    created = await repo.create(version=version)
    assert created.id == version_id
    assert created.state == VersionState.DRAFT

    # Get
    fetched = await repo.get_by_id(version_id=version_id)
    assert fetched is not None
    assert fetched.source_code == "print('hi')"

    # Update
    updated_version = created.model_copy(update={"state": VersionState.ACTIVE})
    updated = await repo.update(version=updated_version)
    assert updated.state == VersionState.ACTIVE

    # Verify persistence
    fetched_again = await repo.get_by_id(version_id=version_id)
    assert fetched_again is not None
    assert fetched_again.state == VersionState.ACTIVE


@pytest.mark.integration
async def test_get_active_and_latest(db_session: AsyncSession, tool: Tool, now: datetime) -> None:
    repo = PostgreSQLToolVersionRepository(db_session)
    user_id = uuid4()
    from skriptoteket.domain.identity.models import AuthProvider, Role
    from skriptoteket.infrastructure.db.models.user import UserModel

    db_session.add(
        UserModel(
            id=user_id,
            email="test2@test.com",
            password_hash="h",
            role=Role.USER,
            auth_provider=AuthProvider.LOCAL,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()

    v1 = ToolVersion(
        id=uuid4(),
        tool_id=tool.id,
        version_number=1,
        state=VersionState.ARCHIVED,
        source_code="v1",
        entrypoint="m",
        content_hash="h",
        created_by_user_id=user_id,
        created_at=now,
    )
    v2 = ToolVersion(
        id=uuid4(),
        tool_id=tool.id,
        version_number=2,
        state=VersionState.ACTIVE,
        source_code="v2",
        entrypoint="m",
        content_hash="h",
        created_by_user_id=user_id,
        created_at=now,
    )
    v3 = ToolVersion(
        id=uuid4(),
        tool_id=tool.id,
        version_number=3,
        state=VersionState.DRAFT,
        source_code="v3",
        entrypoint="m",
        content_hash="h",
        created_by_user_id=user_id,
        created_at=now,
    )

    await repo.create(version=v1)
    await repo.create(version=v2)
    await repo.create(version=v3)

    # Active
    active = await repo.get_active_for_tool(tool_id=tool.id)
    assert active is not None
    assert active.version_number == 2

    # Latest
    latest = await repo.get_latest_for_tool(tool_id=tool.id)
    assert latest is not None
    assert latest.version_number == 3

    # List
    all_versions = await repo.list_for_tool(tool_id=tool.id)
    assert len(all_versions) == 3
    assert all_versions[0].version_number == 3  # Descending order

    # Get next version number
    next_num = await repo.get_next_version_number(tool_id=tool.id)
    assert next_num == 4
