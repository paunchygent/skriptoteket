from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.cli.commands.cleanup_sandbox_snapshots import _cleanup_sandbox_snapshots_async
from skriptoteket.domain.scripting.sandbox_snapshots import SandboxSnapshot
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
async def test_cleanup_sandbox_snapshots_command_deletes_expired(
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
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
        expires_at=now - timedelta(minutes=1),
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
    await db_session.commit()

    monkeypatch.setenv("DATABASE_URL", database_url)

    await _cleanup_sandbox_snapshots_async()

    async with session_factory() as session:
        check_repo = PostgreSQLSandboxSnapshotRepository(session)
        assert await check_repo.get_by_id(snapshot_id=expired_snapshot.id) is None
        assert await check_repo.get_by_id(snapshot_id=active_snapshot.id) is not None
