from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.identity.models import AuthProvider, Role
from skriptoteket.domain.scripting.input_files import InputFileEntry, InputManifest
from skriptoteket.domain.scripting.models import RunContext, RunStatus, ToolRun, VersionState
from skriptoteket.infrastructure.db.models.tool import ToolModel
from skriptoteket.infrastructure.db.models.tool_version import ToolVersionModel
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.repositories.tool_run_repository import PostgreSQLToolRunRepository

pytestmark = pytest.mark.asyncio(loop_scope="module")


async def _create_user(*, db_session: AsyncSession, now: datetime) -> uuid.UUID:
    user_id = uuid.uuid4()
    db_session.add(
        UserModel(
            id=user_id,
            email=f"runner-{user_id.hex[:8]}@example.com",
            password_hash="hash",
            role=Role.USER,
            auth_provider=AuthProvider.LOCAL,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    return user_id


async def _create_tool(
    *,
    db_session: AsyncSession,
    now: datetime,
    owner_user_id: uuid.UUID,
) -> uuid.UUID:
    tool_id = uuid.uuid4()
    db_session.add(
        ToolModel(
            id=tool_id,
            owner_user_id=owner_user_id,
            slug=f"tool-{tool_id.hex[:8]}",
            title="Test tool",
            summary=None,
            is_published=False,
            active_version_id=None,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    return tool_id


async def _create_tool_version(
    *,
    db_session: AsyncSession,
    tool_id: uuid.UUID,
    created_by_user_id: uuid.UUID,
    now: datetime,
) -> uuid.UUID:
    version_id = uuid.uuid4()
    db_session.add(
        ToolVersionModel(
            id=version_id,
            tool_id=tool_id,
            version_number=1,
            state=VersionState.DRAFT,
            source_code="print('hi')",
            entrypoint="run_tool",
            content_hash="hash",
            derived_from_version_id=None,
            created_by_user_id=created_by_user_id,
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
    return version_id


@pytest.mark.integration
async def test_tool_run_create_get_and_update(db_session: AsyncSession) -> None:
    now = datetime.now(timezone.utc)
    user_id = await _create_user(db_session=db_session, now=now)
    tool_id = await _create_tool(db_session=db_session, now=now, owner_user_id=user_id)
    version_id = await _create_tool_version(
        db_session=db_session, tool_id=tool_id, created_by_user_id=user_id, now=now
    )

    repo = PostgreSQLToolRunRepository(db_session)
    run_id = uuid.uuid4()
    running = ToolRun(
        id=run_id,
        tool_id=tool_id,
        version_id=version_id,
        context=RunContext.SANDBOX,
        requested_by_user_id=user_id,
        status=RunStatus.RUNNING,
        started_at=now,
        finished_at=None,
        workdir_path=f"{run_id}/work",
        input_filename="input.txt",
        input_size_bytes=5,
        input_manifest=InputManifest(files=[InputFileEntry(name="input.txt", bytes=5)]),
        html_output=None,
        stdout=None,
        stderr=None,
        artifacts_manifest={},
        error_summary=None,
    )

    created = await repo.create(run=running)
    assert created.id == run_id
    assert created.status is RunStatus.RUNNING

    fetched = await repo.get_by_id(run_id=run_id)
    assert fetched is not None
    assert fetched.input_filename == "input.txt"

    finished_at = now + timedelta(seconds=1)
    completed = fetched.model_copy(
        update={
            "status": RunStatus.SUCCEEDED,
            "finished_at": finished_at,
            "stdout": "ok",
            "stderr": "",
            "html_output": "<p>ok</p>",
            "artifacts_manifest": {"artifacts": []},
            "error_summary": None,
        }
    )
    updated = await repo.update(run=completed)
    assert updated.status is RunStatus.SUCCEEDED
    assert updated.finished_at == finished_at

    fetched_again = await repo.get_by_id(run_id=run_id)
    assert fetched_again is not None
    assert fetched_again.stdout == "ok"


@pytest.mark.integration
async def test_tool_run_get_missing_returns_none(db_session: AsyncSession) -> None:
    repo = PostgreSQLToolRunRepository(db_session)
    missing = await repo.get_by_id(run_id=uuid.uuid4())
    assert missing is None


@pytest.mark.integration
async def test_tool_run_update_missing_raises_not_found(db_session: AsyncSession) -> None:
    from skriptoteket.domain.errors import DomainError, ErrorCode

    now = datetime.now(timezone.utc)
    user_id = await _create_user(db_session=db_session, now=now)
    tool_id = await _create_tool(db_session=db_session, now=now, owner_user_id=user_id)
    version_id = await _create_tool_version(
        db_session=db_session, tool_id=tool_id, created_by_user_id=user_id, now=now
    )

    repo = PostgreSQLToolRunRepository(db_session)
    missing = ToolRun(
        id=uuid.uuid4(),
        tool_id=tool_id,
        version_id=version_id,
        context=RunContext.SANDBOX,
        requested_by_user_id=user_id,
        status=RunStatus.RUNNING,
        started_at=now,
        finished_at=None,
        workdir_path="missing/work",
        input_filename="input.txt",
        input_size_bytes=1,
        input_manifest=InputManifest(files=[InputFileEntry(name="input.txt", bytes=1)]),
        html_output=None,
        stdout=None,
        stderr=None,
        artifacts_manifest={},
        error_summary=None,
    )

    with pytest.raises(DomainError) as exc:
        await repo.update(run=missing)
    assert exc.value.code is ErrorCode.NOT_FOUND
