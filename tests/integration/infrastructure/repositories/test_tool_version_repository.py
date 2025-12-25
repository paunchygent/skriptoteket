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
    owner_user_id = uuid4()

    from skriptoteket.domain.identity.models import AuthProvider, Role
    from skriptoteket.infrastructure.db.models.user import UserModel

    db_session.add(
        UserModel(
            id=owner_user_id,
            email=f"tool-owner-{owner_user_id.hex[:8]}@example.com",
            password_hash="hash",
            role=Role.USER,
            auth_provider=AuthProvider.LOCAL,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    tool = Tool(
        id=tool_id,
        owner_user_id=owner_user_id,
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
        owner_user_id=owner_user_id,
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
        usage_instructions="# Usage\n\nRun the tool.",
        change_summary="Initial version",
        created_by_user_id=user_id,
        created_at=now,
    )
    created = await repo.create(version=version)
    assert created.id == version_id
    assert created.state == VersionState.DRAFT
    assert created.usage_instructions == "# Usage\n\nRun the tool."
    assert created.change_summary == "Initial version"

    # Get
    fetched = await repo.get_by_id(version_id=version_id)
    assert fetched is not None
    assert fetched.source_code == "print('hi')"
    assert fetched.usage_instructions == "# Usage\n\nRun the tool."
    assert fetched.change_summary == "Initial version"

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


@pytest.mark.integration
async def test_update_raises_not_found(db_session: AsyncSession, tool: Tool, now: datetime) -> None:
    repo = PostgreSQLToolVersionRepository(db_session)

    # Create dummy version object but don't persist it
    missing_version = ToolVersion(
        id=uuid4(),
        tool_id=tool.id,
        version_number=1,
        state=VersionState.DRAFT,
        source_code="code",
        entrypoint="main.py",
        content_hash="hash",
        created_by_user_id=uuid4(),
        created_at=now,
    )

    from skriptoteket.domain.errors import DomainError, ErrorCode

    with pytest.raises(DomainError) as exc:
        await repo.update(version=missing_version)
    assert exc.value.code == ErrorCode.NOT_FOUND


@pytest.mark.integration
async def test_get_next_version_number_empty(db_session: AsyncSession, tool: Tool) -> None:
    repo = PostgreSQLToolVersionRepository(db_session)

    # Should be 1 when no versions exist
    next_num = await repo.get_next_version_number(tool_id=tool.id)
    assert next_num == 1


@pytest.mark.integration
async def test_tool_version_review_workflow(
    db_session: AsyncSession, tool: Tool, now: datetime
) -> None:
    """Test that update() persists all review workflow fields."""
    from skriptoteket.domain.identity.models import AuthProvider, Role
    from skriptoteket.infrastructure.db.models.user import UserModel

    repo = PostgreSQLToolVersionRepository(db_session)

    # Create users for the workflow
    author_id = uuid4()
    reviewer_id = uuid4()
    publisher_id = uuid4()

    for uid, email in [
        (author_id, "author@test.com"),
        (reviewer_id, "reviewer@test.com"),
        (publisher_id, "publisher@test.com"),
    ]:
        db_session.add(
            UserModel(
                id=uid,
                email=email,
                password_hash="h",
                role=Role.ADMIN,
                auth_provider=AuthProvider.LOCAL,
                created_at=now,
                updated_at=now,
            )
        )
    await db_session.flush()

    # Create initial draft
    version = ToolVersion(
        id=uuid4(),
        tool_id=tool.id,
        version_number=1,
        state=VersionState.DRAFT,
        source_code="code",
        entrypoint="main.py",
        content_hash="hash",
        created_by_user_id=author_id,
        created_at=now,
    )
    created = await repo.create(version=version)

    # Submit for review
    submitted = created.model_copy(
        update={
            "state": VersionState.IN_REVIEW,
            "submitted_for_review_by_user_id": author_id,
            "submitted_for_review_at": now,
            "change_summary": "Added new feature",
        }
    )
    updated = await repo.update(version=submitted)
    assert updated.state == VersionState.IN_REVIEW
    assert updated.submitted_for_review_by_user_id == author_id
    assert updated.submitted_for_review_at == now
    assert updated.change_summary == "Added new feature"

    # Review and publish
    published = updated.model_copy(
        update={
            "state": VersionState.ACTIVE,
            "reviewed_by_user_id": reviewer_id,
            "reviewed_at": now,
            "review_note": "Looks good!",
            "published_by_user_id": publisher_id,
            "published_at": now,
        }
    )
    updated2 = await repo.update(version=published)
    assert updated2.state == VersionState.ACTIVE
    assert updated2.reviewed_by_user_id == reviewer_id
    assert updated2.reviewed_at == now
    assert updated2.review_note == "Looks good!"
    assert updated2.published_by_user_id == publisher_id
    assert updated2.published_at == now

    # Verify all fields persisted
    fetched = await repo.get_by_id(version_id=version.id)
    assert fetched is not None
    assert fetched.submitted_for_review_by_user_id == author_id
    assert fetched.reviewed_by_user_id == reviewer_id
    assert fetched.published_by_user_id == publisher_id
    assert fetched.change_summary == "Added new feature"
    assert fetched.review_note == "Looks good!"


@pytest.mark.integration
async def test_tool_version_create_with_settings_schema(
    db_session: AsyncSession, tool: Tool, now: datetime
) -> None:
    """Test that create() persists settings_schema and derived_from_version_id."""
    from skriptoteket.domain.identity.models import AuthProvider, Role
    from skriptoteket.domain.scripting.ui.contract_v2 import UiStringField
    from skriptoteket.infrastructure.db.models.user import UserModel

    repo = PostgreSQLToolVersionRepository(db_session)

    user_id = uuid4()
    db_session.add(
        UserModel(
            id=user_id,
            email="schema-test@test.com",
            password_hash="h",
            role=Role.USER,
            auth_provider=AuthProvider.LOCAL,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()

    # Create base version
    base_version = ToolVersion(
        id=uuid4(),
        tool_id=tool.id,
        version_number=1,
        state=VersionState.ACTIVE,
        source_code="v1",
        entrypoint="main.py",
        content_hash="h1",
        created_by_user_id=user_id,
        created_at=now,
    )
    await repo.create(version=base_version)

    # Create derived version with settings_schema
    settings_schema = [
        UiStringField(name="title", label="Document Title"),
        UiStringField(name="author", label="Author Name"),
    ]

    derived_version = ToolVersion(
        id=uuid4(),
        tool_id=tool.id,
        version_number=2,
        state=VersionState.DRAFT,
        source_code="v2",
        entrypoint="main.py",
        content_hash="h2",
        settings_schema=settings_schema,
        derived_from_version_id=base_version.id,
        created_by_user_id=user_id,
        created_at=now,
    )
    created = await repo.create(version=derived_version)

    assert created.derived_from_version_id == base_version.id
    assert created.settings_schema is not None
    assert len(created.settings_schema) == 2
    assert created.settings_schema[0].name == "title"
    assert created.settings_schema[1].name == "author"

    # Verify persistence
    fetched = await repo.get_by_id(version_id=derived_version.id)
    assert fetched is not None
    assert fetched.derived_from_version_id == base_version.id
    assert fetched.settings_schema is not None
    assert len(fetched.settings_schema) == 2
    assert fetched.settings_schema[0].name == "title"
    assert fetched.settings_schema[0].label == "Document Title"
