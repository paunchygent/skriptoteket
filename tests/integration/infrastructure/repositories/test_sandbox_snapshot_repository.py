from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.scripting.sandbox_snapshots import SandboxSnapshot
from skriptoteket.domain.scripting.tool_inputs import (
    ToolInputFieldKind,
    ToolInputStringField,
)
from skriptoteket.domain.scripting.ui.contract_v2 import (
    UiActionFieldKind,
    UiStringField,
)
from skriptoteket.infrastructure.repositories.sandbox_snapshot_repository import (
    PostgreSQLSandboxSnapshotRepository,
)
from tests.integration.infrastructure.repositories.sandbox_snapshot_test_support import (
    create_tool,
    create_tool_version,
    create_user,
)

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.mark.integration
async def test_sandbox_snapshot_create_and_get_roundtrip(
    db_session: AsyncSession,
) -> None:
    now = datetime.now(timezone.utc)
    user_id = await create_user(db_session=db_session, now=now)
    tool_id = await create_tool(db_session=db_session, now=now, owner_user_id=user_id)
    version_id = await create_tool_version(
        db_session=db_session, tool_id=tool_id, created_by_user_id=user_id, now=now
    )

    settings_schema = [UiStringField(name="title", label="Title")]
    input_schema = [ToolInputStringField(name="query", label="Query")]

    snapshot = SandboxSnapshot(
        id=uuid.uuid4(),
        tool_id=tool_id,
        draft_head_id=version_id,
        created_by_user_id=user_id,
        entrypoint="run_tool",
        source_code="print('hi')",
        settings_schema=settings_schema,
        input_schema=input_schema,
        usage_instructions="Use it",
        payload_bytes=128,
        created_at=now,
        expires_at=now + timedelta(hours=24),
    )

    repo = PostgreSQLSandboxSnapshotRepository(db_session)
    created = await repo.create(snapshot=snapshot)

    assert created.id == snapshot.id
    assert created.tool_id == tool_id
    assert created.draft_head_id == version_id
    assert created.created_by_user_id == user_id
    assert created.entrypoint == "run_tool"
    assert created.source_code == "print('hi')"
    assert created.usage_instructions == "Use it"
    assert created.payload_bytes == 128
    assert created.settings_schema is not None
    assert created.settings_schema[0].kind is UiActionFieldKind.STRING
    assert created.settings_schema[0].name == "title"
    assert created.input_schema is not None
    assert created.input_schema[0].kind is ToolInputFieldKind.STRING
    assert created.input_schema[0].name == "query"

    fetched = await repo.get_by_id(snapshot_id=snapshot.id)
    assert fetched is not None
    assert fetched.id == snapshot.id
    assert fetched.entrypoint == "run_tool"
    assert fetched.settings_schema is not None
    assert fetched.settings_schema[0].kind is UiActionFieldKind.STRING
    assert fetched.input_schema is not None
    assert fetched.input_schema[0].kind is ToolInputFieldKind.STRING


@pytest.mark.integration
async def test_sandbox_snapshot_delete_expired_removes_only_expired(
    db_session: AsyncSession,
) -> None:
    now = datetime.now(timezone.utc)
    user_id = await create_user(db_session=db_session, now=now)
    tool_id = await create_tool(db_session=db_session, now=now, owner_user_id=user_id)
    version_id = await create_tool_version(
        db_session=db_session, tool_id=tool_id, created_by_user_id=user_id, now=now
    )

    repo = PostgreSQLSandboxSnapshotRepository(db_session)

    expired_snapshot = SandboxSnapshot(
        id=uuid.uuid4(),
        tool_id=tool_id,
        draft_head_id=version_id,
        created_by_user_id=user_id,
        entrypoint="run_tool",
        source_code="print('expired')",
        settings_schema=None,
        input_schema=None,
        usage_instructions=None,
        payload_bytes=64,
        created_at=now - timedelta(hours=2),
        expires_at=now - timedelta(minutes=5),
    )
    active_snapshot = SandboxSnapshot(
        id=uuid.uuid4(),
        tool_id=tool_id,
        draft_head_id=version_id,
        created_by_user_id=user_id,
        entrypoint="run_tool",
        source_code="print('active')",
        settings_schema=None,
        input_schema=None,
        usage_instructions=None,
        payload_bytes=64,
        created_at=now,
        expires_at=now + timedelta(hours=1),
    )

    await repo.create(snapshot=expired_snapshot)
    await repo.create(snapshot=active_snapshot)

    deleted = await repo.delete_expired(now=now)

    assert deleted == 1
    assert await repo.get_by_id(snapshot_id=expired_snapshot.id) is None
    assert await repo.get_by_id(snapshot_id=active_snapshot.id) is not None
